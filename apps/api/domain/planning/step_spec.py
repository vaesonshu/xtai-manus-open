"""规划步骤规格值对象：Planner 产出的结构化步骤描述。"""

from __future__ import annotations

from dataclasses import dataclass

from domain.agent.role import AgentRole
from domain.exceptions import ValidationError


@dataclass(frozen=True)
class PlanStepSpec:
    """单步规划规格，包含执行角色与描述。"""

    description: str
    agent_role: AgentRole = AgentRole.EXECUTOR

    def __post_init__(self) -> None:
        if not self.description or not self.description.strip():
            raise ValidationError("plan step description must not be empty")

    @classmethod
    def from_dict(cls, payload: dict) -> PlanStepSpec:
        """从 LLM 结构化输出解析步骤规格。"""
        description = str(payload.get("description", "")).strip()
        role_raw = str(payload.get("agent_role", AgentRole.EXECUTOR.value))
        return cls(
            description=description,
            agent_role=AgentRole.from_value(role_raw),
        )
