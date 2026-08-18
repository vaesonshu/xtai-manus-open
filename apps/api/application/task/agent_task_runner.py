"""Agent 任务运行器：串联记忆、规划与步骤执行循环。"""

from __future__ import annotations

import logging

from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from domain.agent.role import AgentRole
from domain.event import (
    assistant_message,
    done_event,
    plan_completed,
    plan_created,
    plan_updated,
    step_completed,
    step_started,
    user_message,
)
from domain.event.base import StreamEvent
from domain.memory.kind import MemoryKind
from domain.planning.step_spec import PlanStepSpec
from domain.ports.task import TaskRepository
from domain.task.identifiers import TaskId
from domain.task.ports import TaskExecutionPort
from domain.task.task import AgentTask

logger = logging.getLogger(__name__)


class AgentTaskRunner:
    """多 Agent 任务运行器（``create_plan → 逐步执行 → 每步 update_plan``）。"""

    def __init__(
        self,
        *,
        memory_service: MemoryApplicationService,
        planning_service: PlanningApplicationService,
        task_repository: TaskRepository,
        use_llm_planning: bool = False,
        replan_after_each_step: bool = True,
    ) -> None:
        self._memory = memory_service
        self._planning = planning_service
        self._tasks = task_repository
        self._use_llm_planning = use_llm_planning
        self._replan_after_each_step = replan_after_each_step

    async def invoke(self, execution: TaskExecutionPort) -> None:
        """驱动一次完整的 Agent 任务执行。"""
        task_id = TaskId(execution.task_id)
        goal = await self._read_goal(execution)
        agent_task = AgentTask.create(goal=goal, task_id=task_id)
        self._tasks.save(agent_task)

        await self._emit(execution, user_message(goal))
        self._memory.add_agent_message(
            task_id,
            AgentRole.COORDINATOR,
            {"role": "user", "content": goal},
        )
        self._memory.record(
            task_id,
            kind=MemoryKind.EPISODIC,
            content=f"用户目标：{goal}",
            agent_role=AgentRole.COORDINATOR,
        )

        plan = await self._create_plan(task_id=task_id, goal=goal)
        agent_task.attach_plan(plan)
        agent_task.start()
        self._tasks.save(agent_task)
        await self._emit(execution, plan_created(plan))
        if plan.message:
            await self._emit(execution, assistant_message(plan.message))

        while agent_task.plan is not None:
            next_step = agent_task.plan.get_next_step()
            if next_step is None:
                break

            step = agent_task.begin_next_step()
            await self._emit(execution, step_started(step))

            result = self._execute_step(step)
            agent_task.complete_current_step(result)

            self._memory.add_agent_message(
                task_id,
                step.agent_role,
                {"role": "assistant", "content": result},
            )
            self._memory.record(
                task_id,
                kind=MemoryKind.WORKING,
                content=result,
                agent_role=step.agent_role,
            )
            self._memory.compact_conversations(task_id)
            self._tasks.save(agent_task)

            await self._emit(execution, step_completed(step))
            await self._emit(execution, assistant_message(result))

            if (
                self._replan_after_each_step
                and self._use_llm_planning
                and agent_task.plan.get_next_step() is not None
            ):
                await self._planning.update_plan_after_step(agent_task, step)
                self._tasks.save(agent_task)
                if agent_task.plan is not None:
                    await self._emit(execution, plan_updated(agent_task.plan))

        agent_task.complete(
            result={
                "goal": goal,
                "plan_versions": len(agent_task.plan_history),
                "steps_total": len(agent_task.plan.steps) if agent_task.plan else 0,
            }
        )
        self._tasks.save(agent_task)
        if agent_task.plan is not None:
            await self._emit(execution, plan_completed(agent_task.plan))
        await self._emit(execution, done_event())

    async def destroy(self) -> None:
        """释放运行器资源（当前无状态，预留扩展）。"""
        return None

    async def on_done(self, execution: TaskExecutionPort) -> None:
        """任务结束回调：压缩记忆并清理工作区。"""
        task_id = TaskId(execution.task_id)
        self._memory.clear_working(task_id)
        self._memory.compact_conversations(task_id)
        logger.info("任务[%s]执行结束，记忆已压缩", task_id)

    async def _read_goal(self, execution: TaskExecutionPort) -> str:
        """从输入流读取用户目标。"""
        _message_id, payload = await execution.input_stream.get(block_ms=5000)
        if isinstance(payload, dict):
            goal = str(payload.get("goal") or payload.get("content") or "").strip()
            if goal:
                return goal
        if isinstance(payload, str) and payload.strip():
            return payload.strip()
        return "未指定目标"

    async def _create_plan(self, *, task_id: TaskId, goal: str):
        if self._use_llm_planning:
            return await self._planning.create_plan(task_id=task_id, goal=goal)
        return self._planning.create_plan_offline(
            goal=goal,
            title=f"规划：{goal}",
            step_specs=[
                PlanStepSpec(
                    description=f"调研并收集与「{goal}」相关的资料",
                    agent_role=AgentRole.RESEARCHER,
                ),
                PlanStepSpec(
                    description="整理方案并生成可交付输出",
                    agent_role=AgentRole.CODER,
                ),
                PlanStepSpec(
                    description="复核输出质量与完整性",
                    agent_role=AgentRole.REVIEWER,
                ),
            ],
        )

    @staticmethod
    def _execute_step(step) -> str:
        """执行单步（当前为占位实现，后续接入 LLM / 工具）。"""
        return f"[{step.agent_role.value}] 已完成：{step.description}"

    @staticmethod
    async def _emit(execution: TaskExecutionPort, event: StreamEvent) -> None:
        await execution.output_stream.put(event.as_dict())
