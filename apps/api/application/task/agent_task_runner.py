"""Agent 任务运行器：串联记忆、规划与步骤执行循环。"""

from __future__ import annotations

import logging

from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.agent.step_executor import (
    OfflineStepExecutor,
    StepExecutionContext,
    StepExecutor,
)
from application.agent.step_result import StepExecutionResult
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
    wait_event,
)
from domain.event.base import StreamEvent
from domain.exceptions import WaitForUserInputError
from domain.memory.kind import MemoryKind
from domain.planning.step_spec import PlanStepSpec
from domain.ports.task import TaskRepository
from domain.task.identifiers import TaskId
from domain.task.ports import TaskExecutionPort
from domain.task.status import ExecutionStatus, TaskStatus
from domain.task.step import TaskStep
from domain.task.task import AgentTask

logger = logging.getLogger(__name__)

StepExecutorLike = StepExecutor | OfflineStepExecutor


class AgentTaskRunner:
    """多 Agent 任务运行器（``create_plan → 逐步执行 → 每步 update_plan``）。"""

    def __init__(
        self,
        *,
        memory_service: MemoryApplicationService,
        planning_service: PlanningApplicationService,
        task_repository: TaskRepository,
        step_executor: StepExecutorLike | None = None,
        use_llm_planning: bool = False,
        replan_after_each_step: bool = True,
    ) -> None:
        self._memory = memory_service
        self._planning = planning_service
        self._tasks = task_repository
        self._step_executor = step_executor or OfflineStepExecutor()
        self._use_llm_planning = use_llm_planning
        self._replan_after_each_step = replan_after_each_step

    def should_keep_execution_alive(self, task_id: TaskId) -> bool:
        """WAITING 状态下保留执行实例，以便用户回复后继续。"""
        agent_task = self._tasks.get(task_id)
        return agent_task is not None and agent_task.status is TaskStatus.WAITING

    async def invoke(self, execution: TaskExecutionPort) -> None:
        """驱动一次完整的 Agent 任务执行（支持新建与 WAITING 恢复）。"""
        task_id = TaskId(execution.task_id)
        agent_task = self._tasks.get(task_id)

        if agent_task is not None and agent_task.status is TaskStatus.WAITING:
            await self._resume_from_waiting(execution, agent_task, task_id)
            return

        goal = await self._read_goal(execution)
        if agent_task is not None and agent_task.status is TaskStatus.RUNNING:
            self._memory.rollback_for_user_input(
                task_id,
                AgentRole.COORDINATOR,
                goal,
            )
            await self._emit(execution, user_message(goal))
            await self._run_execution_loop(execution, agent_task, task_id, goal)
            return

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

        await self._run_execution_loop(execution, agent_task, task_id, goal)

    async def destroy(self) -> None:
        """释放运行器资源（当前无状态，预留扩展）。"""
        return None

    async def on_done(self, execution: TaskExecutionPort) -> None:
        """任务结束回调：压缩记忆并清理工作区。"""
        task_id = TaskId(execution.task_id)
        agent_task = self._tasks.get(task_id)
        if agent_task is not None and agent_task.status is TaskStatus.WAITING:
            logger.info("任务[%s]处于等待用户输入，跳过 on_done 清理", task_id)
            return
        self._memory.clear_working(task_id)
        self._memory.compact_conversations(task_id)
        logger.info("任务[%s]执行结束，记忆已压缩", task_id)

    async def _resume_from_waiting(
        self,
        execution: TaskExecutionPort,
        agent_task: AgentTask,
        task_id: TaskId,
    ) -> None:
        """从 WAITING 状态恢复：智能回滚记忆并继续当前步骤。"""
        user_input = await self._read_goal(execution)
        await self._emit(execution, user_message(user_input))

        waiting_role = agent_task.waiting_agent_role or AgentRole.COORDINATOR
        self._memory.rollback_for_user_input(task_id, waiting_role, user_input)

        agent_task.resume()
        self._tasks.save(agent_task)

        step = self._get_running_step(agent_task)
        if step is None:
            agent_task.fail("恢复执行失败：无运行中的步骤")
            self._tasks.save(agent_task)
            return

        try:
            result = await self._execute_step(
                task_id,
                step,
                execution,
                resume=True,
                user_message=agent_task.goal,
            )
        except WaitForUserInputError as exc:
            await self._handle_wait_for_user(execution, agent_task, exc)
            return

        await self._after_step_success(execution, agent_task, task_id, step, result)
        await self._run_execution_loop(execution, agent_task, task_id, agent_task.goal)

    async def _run_execution_loop(
        self,
        execution: TaskExecutionPort,
        agent_task: AgentTask,
        task_id: TaskId,
        goal: str,
    ) -> None:
        """步骤执行主循环。"""
        while agent_task.plan is not None:
            running_step = self._get_running_step(agent_task)
            if running_step is not None:
                step = running_step
            else:
                next_step = agent_task.plan.get_next_step()
                if next_step is None:
                    break
                step = agent_task.begin_next_step()
                await self._emit(execution, step_started(step))

            try:
                result = await self._execute_step(
                    task_id,
                    step,
                    execution,
                    user_message=goal,
                )
            except WaitForUserInputError as exc:
                await self._handle_wait_for_user(execution, agent_task, exc)
                return

            await self._after_step_success(
                execution,
                agent_task,
                task_id,
                step,
                result,
            )

            if (
                self._replan_after_each_step
                and self._use_llm_planning
                and agent_task.plan is not None
                and agent_task.plan.get_next_step() is not None
            ):
                await self._planning.update_plan_after_step(agent_task, step)
                self._tasks.save(agent_task)
                if agent_task.plan is not None:
                    await self._emit(execution, plan_updated(agent_task.plan))

        summary_payload = await self._summarize_and_emit(execution, task_id, goal)
        agent_task.complete(
            result={
                "goal": goal,
                "plan_versions": len(agent_task.plan_history),
                "steps_total": len(agent_task.plan.steps) if agent_task.plan else 0,
                **summary_payload,
            }
        )
        self._tasks.save(agent_task)
        if agent_task.plan is not None:
            await self._emit(execution, plan_completed(agent_task.plan))
        await self._emit(execution, done_event())

    async def _after_step_success(
        self,
        execution: TaskExecutionPort,
        agent_task: AgentTask,
        task_id: TaskId,
        step: TaskStep,
        result: StepExecutionResult,
    ) -> None:
        """步骤成功后的记忆写入与事件推送。"""
        agent_task.complete_current_step(
            result.display_text,
            success=result.success,
            attachments=result.attachments,
        )

        self._memory.add_agent_message(
            task_id,
            step.agent_role,
            {"role": "assistant", "content": result.display_text},
        )
        self._memory.record(
            task_id,
            kind=MemoryKind.WORKING,
            content=result.display_text,
            agent_role=step.agent_role,
        )
        self._memory.compact_conversations(task_id)
        self._tasks.save(agent_task)

        await self._emit(execution, step_completed(step))
        if result.display_text:
            await self._emit(execution, assistant_message(result.display_text))

    async def _handle_wait_for_user(
        self,
        execution: TaskExecutionPort,
        agent_task: AgentTask,
        exc: WaitForUserInputError,
    ) -> None:
        """进入 WAITING 状态并推送等待事件（不发送 done）。"""
        agent_task.wait_for_input(exc.message, agent_role=exc.agent_role)
        self._tasks.save(agent_task)
        await self._emit(
            execution,
            wait_event(reason=exc.message, question=exc.question),
        )
        await self._emit(execution, assistant_message(exc.question))
        logger.info(
            "任务[%s]等待用户输入，agent=%s",
            agent_task.task_id,
            exc.agent_role.value,
        )

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

    async def _execute_step(
        self,
        task_id: TaskId,
        step: TaskStep,
        execution: TaskExecutionPort,
        *,
        resume: bool = False,
        user_message: str = "",
    ) -> StepExecutionResult:
        """执行单步：委托 StepExecutor / ReActExecutor，并转发工具等事件。"""

        async def on_event(event: StreamEvent) -> None:
            await self._emit(execution, event)

        return await self._step_executor.execute(
            task_id=task_id,
            step=step,
            context=StepExecutionContext(message=user_message),
            on_event=on_event,
            resume=resume,
        )

    async def _summarize_and_emit(
        self,
        execution: TaskExecutionPort,
        task_id: TaskId,
        goal: str,
    ) -> dict[str, object]:
        """任务结束时生成汇总并推送助手消息。"""
        summarize = getattr(self._step_executor, "summarize", None)
        if summarize is None:
            return {}
        try:
            summary = await summarize(task_id=task_id, goal=goal)
        except Exception:  # noqa: BLE001
            logger.exception("任务汇总失败，跳过 summarize")
            return {}
        if summary.message:
            await self._emit(execution, assistant_message(summary.message))
        return {
            "summary": summary.message,
            "attachments": list(summary.attachments),
        }

    @staticmethod
    def _get_running_step(agent_task: AgentTask) -> TaskStep | None:
        """获取当前运行中的步骤（WAITING 恢复时使用）。"""
        if agent_task.plan is None:
            return None
        return next(
            (
                item
                for item in agent_task.plan.steps
                if item.status is ExecutionStatus.RUNNING
            ),
            None,
        )

    @staticmethod
    async def _emit(execution: TaskExecutionPort, event: StreamEvent) -> None:
        await execution.output_stream.put(event.as_dict())
