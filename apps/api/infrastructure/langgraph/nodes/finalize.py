"""summarize / complete / fail 节点。"""

from __future__ import annotations

import logging

from domain.event import assistant_message, done_event, error_event, plan_completed
from domain.task.identifiers import TaskId
from domain.task.status import TaskStatus
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.helpers import require_agent_task
from infrastructure.langgraph.state import AgentState

logger = logging.getLogger(__name__)


def make_summarize_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：任务结束前汇总交付。"""

    async def summarize(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        goal = state["goal"]
        agent_task = require_agent_task(deps, task_id)
        deliverables = agent_task.primary_deliverable()
        summary_payload: dict[str, object] = {}

        summarize_fn = getattr(deps.step_executor, "summarize", None)
        if summarize_fn is not None:

            async def on_event(event) -> None:
                await emitter.emit(event)

            try:
                summary = await summarize_fn(
                    task_id=task_id,
                    goal=goal,
                    on_event=on_event,
                    deliverables=deliverables,
                )
                summary_payload = {
                    "summary": summary.message,
                    "attachments": [
                        attachment.to_dict() for attachment in summary.attachments
                    ],
                }
            except Exception:  # noqa: BLE001
                logger.exception("任务[%s] summarize 失败", task_id)
                if deliverables:
                    await emitter.emit(assistant_message(deliverables))
                    summary_payload = {"summary": deliverables, "attachments": []}

        return {"summary": summary_payload}

    return summarize


def make_complete_task_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：标记任务完成并推送 done。"""

    async def complete_task(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        goal = state["goal"]
        agent_task = require_agent_task(deps, task_id)
        summary = state.get("summary") or {}

        result = {
            "goal": goal,
            "plan_versions": len(agent_task.plan_history),
            "steps_total": len(agent_task.plan.steps) if agent_task.plan else 0,
            **summary,
        }
        agent_task.complete(result=result)
        deps.task_repository.save(agent_task)

        if agent_task.plan is not None:
            await emitter.emit(plan_completed(agent_task.plan))
        await emitter.emit(done_event())

        return {
            "agent_task_status": TaskStatus.COMPLETED.value,
            "result": result,
        }

    return complete_task


def make_fail_task_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：标记任务失败。"""

    async def fail_task(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        error = str(state.get("error") or "任务执行失败")
        agent_task = require_agent_task(deps, task_id)
        agent_task.fail(error)
        deps.task_repository.save(agent_task)
        await emitter.emit(error_event(error))
        return {
            "agent_task_status": TaskStatus.FAILED.value,
            "error": error,
        }

    return fail_task
