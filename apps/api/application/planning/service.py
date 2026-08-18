"""多 Agent 规划应用服务。"""

from __future__ import annotations

import logging

from pydantic import ValidationError as PydanticValidationError

from application.memory.service import MemoryApplicationService
from application.planning.dto import LlmPlanOutput
from application.planning.schema import (
    PLANNER_SYSTEM_PROMPT,
    PLAN_RESPONSE_FORMAT,
    REPLANNER_SYSTEM_PROMPT,
)
from domain.agent.role import AgentRole
from domain.exceptions import ValidationError
from domain.memory.kind import MemoryKind
from domain.planning.builder import PlanBuilder
from domain.planning.step_spec import PlanStepSpec
from domain.ports import LlmRuntimePort
from domain.task.identifiers import TaskId
from domain.task.plan import TaskPlan
from domain.task.step import TaskStep
from domain.task.task import AgentTask

logger = logging.getLogger(__name__)


class PlanningApplicationService:
    """规划用例服务：结合记忆上下文调用 LLM 生成/调整 ``TaskPlan``。"""

    def __init__(
        self,
        llm_runtime: LlmRuntimePort,
        memory_service: MemoryApplicationService,
    ) -> None:
        self._llm_runtime = llm_runtime
        self._memory = memory_service

    async def create_plan(
        self,
        *,
        task_id: TaskId,
        goal: str,
        title: str | None = None,
    ) -> TaskPlan:
        """为目标生成多 Agent 规划，并写入 episodic 记忆。"""
        memory_context = self._memory.build_context(task_id)
        output = await self._invoke_planner(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=self._build_user_prompt(goal=goal, memory_context=memory_context),
        )
        plan = self._build_plan_from_output(
            goal=goal,
            title=title or output.title,
            output=output,
        )
        self._memory.record(
            task_id,
            kind=MemoryKind.EPISODIC,
            content=f"已生成规划：{plan.title}，共 {len(plan.steps)} 步",
            agent_role=AgentRole.PLANNER,
        )
        return plan

    async def replan(
        self,
        task: AgentTask,
        *,
        reason: str,
    ) -> list[TaskStep]:
        """基于记忆与原因对任务进行动态重规划。"""
        if task.plan is None:
            raise ValidationError("task has no attached plan")

        memory_context = self._memory.build_context(task.task_id)
        output = await self._invoke_planner(
            system_prompt=REPLANNER_SYSTEM_PROMPT,
            user_prompt=self._build_replan_prompt(
                goal=task.goal,
                reason=reason,
                memory_context=memory_context,
                current_plan=task.plan,
            ),
        )
        added = task.replan(output.to_step_specs(), reason=reason)
        self._memory.record(
            task.task_id,
            kind=MemoryKind.EPISODIC,
            content=f"重规划：{reason}，新增 {len(added)} 步",
            agent_role=AgentRole.PLANNER,
        )
        return added

    async def update_plan_after_step(
        self,
        task: AgentTask,
        completed_step: TaskStep,
        *,
        reason: str | None = None,
    ) -> list[TaskStep]:
        """步骤完成后更新规划（Planner 每步迭代模式）。"""
        update_reason = reason or (
            f"步骤 [{completed_step.agent_role.value}] "
            f"「{completed_step.description}」已完成，结果：{completed_step.result}"
        )
        return await self.replan(task, reason=update_reason)

    def create_plan_offline(
        self,
        *,
        goal: str,
        title: str,
        step_specs: list[PlanStepSpec],
    ) -> TaskPlan:
        """不调用 LLM 的确定性规划（测试与降级路径）。"""
        return PlanBuilder.build(title=title, goal=goal, step_specs=step_specs)

    async def _invoke_planner(self, *, system_prompt: str, user_prompt: str) -> LlmPlanOutput:
        provider = self._llm_runtime.get_provider()
        message = await provider.invoke(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=PLAN_RESPONSE_FORMAT,
        )
        content = message.get("content")
        if not content:
            raise ValidationError("planner returned empty content")
        try:
            return LlmPlanOutput.model_validate_json(content)
        except PydanticValidationError as exc:
            logger.exception("规划输出校验失败")
            raise ValidationError("planner returned invalid plan output") from exc

    @staticmethod
    def _build_plan_from_output(
        *,
        goal: str,
        title: str,
        output: LlmPlanOutput,
    ) -> TaskPlan:
        specs = output.to_step_specs()
        if not specs:
            raise ValidationError("planner returned empty steps")
        return PlanBuilder.build(
            title=title,
            goal=goal,
            message=output.message,
            step_specs=specs,
        )

    @staticmethod
    def _build_user_prompt(*, goal: str, memory_context: str) -> str:
        memory_block = memory_context or "（无历史记忆）"
        return f"目标：{goal}\n\n相关记忆：\n{memory_block}"

    @staticmethod
    def _build_replan_prompt(
        *,
        goal: str,
        reason: str,
        memory_context: str,
        current_plan: TaskPlan,
    ) -> str:
        completed = [
            f"- [{step.agent_role.value}] {step.description} => {step.result or step.status.value}"
            for step in current_plan.steps
            if step.done
        ]
        pending = [
            f"- [{step.agent_role.value}] {step.description}"
            for step in current_plan.steps
            if not step.done
        ]
        return (
            f"目标：{goal}\n"
            f"重规划原因：{reason}\n\n"
            f"已完成步骤：\n{chr(10).join(completed) or '（无）'}\n\n"
            f"未完成步骤（将被跳过）：\n{chr(10).join(pending) or '（无）'}\n\n"
            f"相关记忆：\n{memory_context or '（无）'}"
        )
