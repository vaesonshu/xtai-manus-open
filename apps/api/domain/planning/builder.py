"""规划领域服务：将步骤规格组装为 ``TaskPlan``。"""

from __future__ import annotations

from domain.planning.step_spec import PlanStepSpec
from domain.task.plan import TaskPlan
from domain.task.step import TaskStep


class PlanBuilder:
    """多 Agent 规划构建器（纯领域逻辑，不调用 LLM）。"""

    @staticmethod
    def build(
        *,
        title: str,
        goal: str,
        step_specs: list[PlanStepSpec],
        language: str = "zh-CN",
        message: str = "",
    ) -> TaskPlan:
        """根据步骤规格创建完整 ``TaskPlan``。"""
        plan = TaskPlan.create(
            title=title,
            goal=goal,
            language=language,
            message=message,
        )
        for spec in step_specs:
            plan.add_step(spec.description, agent_role=spec.agent_role)
        return plan

    @staticmethod
    def specs_from_steps(steps: list[TaskStep]) -> list[PlanStepSpec]:
        """将已有步骤转为规格列表（replan 时复用）。"""
        return [
            PlanStepSpec(description=step.description, agent_role=step.agent_role)
            for step in steps
        ]
