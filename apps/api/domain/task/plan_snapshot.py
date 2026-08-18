"""规划快照：记录规划版本历史，支持审计与回溯。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.task.identifiers import PlanId
from domain.task.plan import TaskPlan


@dataclass(frozen=True)
class PlanSnapshot:
    """某一时刻的规划快照。"""

    version: int
    plan_id: PlanId
    title: str
    goal: str
    reason: str
    steps: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_plan(cls, plan: TaskPlan, *, version: int, reason: str = "") -> PlanSnapshot:
        """从当前 ``TaskPlan`` 创建快照。"""
        serialized = tuple(
            {
                "step_id": str(step.step_id),
                "description": step.description,
                "agent_role": step.agent_role.value,
                "status": step.status.value,
                "result": step.result,
                "error": step.error,
            }
            for step in plan.steps
        )
        return cls(
            version=version,
            plan_id=plan.plan_id,
            title=plan.title,
            goal=plan.goal,
            reason=reason,
            steps=serialized,
        )
