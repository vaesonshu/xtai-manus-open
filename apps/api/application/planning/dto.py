"""规划应用层 DTO：LLM 结构化输出的 Pydantic 模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from domain.agent.role import AgentRole
from domain.planning.step_spec import PlanStepSpec

# LLM 可输出的 Agent 角色字面量
AgentRoleLiteral = Literal[
    "coordinator",
    "planner",
    "researcher",
    "coder",
    "reviewer",
    "executor",
]


class PlanStepDto(BaseModel):
    """规划步骤 DTO（LLM → Application 边界）。"""

    model_config = ConfigDict(extra="forbid")

    agent_role: AgentRoleLiteral = "executor"
    description: str = Field(..., min_length=1)

    def to_spec(self) -> PlanStepSpec:
        """转换为领域层 ``PlanStepSpec``。"""
        return PlanStepSpec(
            description=self.description,
            agent_role=AgentRole.from_value(self.agent_role),
        )


class LlmPlanOutput(BaseModel):
    """LLM 规划输出 DTO。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    message: str = ""
    steps: list[PlanStepDto] = Field(..., min_length=1)

    def to_step_specs(self) -> list[PlanStepSpec]:
        """批量转换为领域步骤规格。"""
        return [step.to_spec() for step in self.steps]
