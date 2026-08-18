"""execute / begin / resume 节点：驱动单步 ReAct 执行。"""

from __future__ import annotations

from application.agent.step_executor import StepExecutionContext
from domain.agent.role import AgentRole
from domain.event import step_completed, step_started, user_message
from domain.event.base import StreamEvent
from domain.exceptions import WaitForUserInputError
from domain.memory.kind import MemoryKind
from domain.task.identifiers import TaskId
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.helpers import get_running_step, require_agent_task
from infrastructure.langgraph.state import AgentState


def make_begin_step_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：开始执行规划中的下一步。"""

    async def begin_step(state: AgentState) -> dict:
        agent_task = require_agent_task(deps, TaskId(state["task_id"]))
        step = agent_task.begin_next_step()
        deps.task_repository.save(agent_task)
        await emitter.emit(step_started(step))
        return {
            "current_step_index": state.get("current_step_index", 0),
            "resume_step": False,
        }

    return begin_step


def make_execute_step_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：执行当前步骤（含 ReAct 工具循环）。"""

    async def execute_step(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        agent_task = require_agent_task(deps, task_id)
        step = get_running_step(agent_task)
        if step is None:
            return {"error": "无运行中的步骤可执行"}

        resume = bool(state.get("resume_step"))

        async def on_event(event: StreamEvent) -> None:
            await emitter.emit(event)

        try:
            result = await deps.step_executor.execute(
                task_id=task_id,
                step=step,
                context=StepExecutionContext(message=state["goal"]),
                on_event=on_event,
                resume=resume,
            )
        except WaitForUserInputError as exc:
            return {
                "waiting_question": exc.question,
                "waiting_agent_role": exc.agent_role.value,
                "resume_step": False,
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc), "resume_step": False}

        return {
            "last_step_result": {
                "success": result.success,
                "result": result.result,
                "raw_content": result.raw_content,
                "display_text": result.display_text,
                "attachments": list(result.attachments),
            },
            "waiting_question": None,
            "waiting_agent_role": None,
            "resume_step": False,
        }

    return execute_step


def make_after_step_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：步骤成功后的记忆写入与事件推送。"""

    async def after_step(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        agent_task = require_agent_task(deps, task_id)
        raw = state.get("last_step_result") or {}
        display_text = str(raw.get("display_text") or raw.get("result") or "")
        attachments = tuple(raw.get("attachments") or ())

        step = agent_task.complete_current_step(
            display_text,
            success=bool(raw.get("success", True)),
            attachments=attachments,
        )
        deps.memory_service.add_agent_message(
            task_id,
            step.agent_role,
            {"role": "assistant", "content": display_text},
        )
        deps.memory_service.record(
            task_id,
            kind=MemoryKind.WORKING,
            content=display_text,
            agent_role=step.agent_role,
        )
        deps.memory_service.compact_conversations(task_id)
        deps.task_repository.save(agent_task)

        await emitter.emit(step_completed(step))

        return {
            "current_step_index": state.get("current_step_index", 0) + 1,
            "last_step_result": None,
        }

    return after_step


def make_resume_step_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：用户回复后回滚记忆并恢复执行。"""

    async def resume_step(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        user_input = str(state.get("user_reply") or "").strip()
        if not user_input:
            return {"error": "用户回复为空"}

        agent_task = require_agent_task(deps, task_id)
        await emitter.emit(user_message(user_input))

        waiting_role = agent_task.waiting_agent_role or AgentRole.COORDINATOR
        deps.memory_service.rollback_for_user_input(
            task_id,
            waiting_role,
            user_input,
        )
        agent_task.resume()
        deps.task_repository.save(agent_task)

        return {"resume_step": True, "user_reply": None}

    return resume_step
