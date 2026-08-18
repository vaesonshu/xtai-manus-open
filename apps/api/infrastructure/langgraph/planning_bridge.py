"""LangGraph 与领域规划模型的适配器。"""

from __future__ import annotations

from typing import Any

from domain.agent.role import AgentRole
from domain.planning.builder import PlanBuilder
from domain.planning.step_spec import PlanStepSpec
from domain.task.plan import TaskPlan


def default_multi_agent_specs(goal: str) -> list[PlanStepSpec]:
    """无 LLM 时的多 Agent 默认规划（图节点降级路径）。"""
    return [
        PlanStepSpec(
            description=f"调研并收集与「{goal}」相关的资料与约束",
            agent_role=AgentRole.RESEARCHER,
        ),
        PlanStepSpec(
            description="基于调研结果整理方案并生成可交付输出",
            agent_role=AgentRole.CODER,
        ),
        PlanStepSpec(
            description="复核输出质量、风险与完整性，必要时提出修改建议",
            agent_role=AgentRole.REVIEWER,
        ),
    ]


def build_offline_plan(goal: str, *, title: str | None = None) -> TaskPlan:
    """构建离线多 Agent 规划。"""
    return PlanBuilder.build(
        title=title or f"规划：{goal}",
        goal=goal,
        step_specs=default_multi_agent_specs(goal),
    )


def plan_to_state_steps(plan: TaskPlan) -> list[dict[str, str]]:
    """将 ``TaskPlan`` 序列化为 LangGraph 状态中的步骤列表。"""
    return [
        {
            "step_id": str(step.step_id),
            "description": step.description,
            "agent_role": step.agent_role.value,
            "status": step.status.value,
        }
        for step in plan.steps
    ]


def specs_from_state_steps(steps: list[dict[str, Any]]) -> list[PlanStepSpec]:
    """从 LangGraph 状态步骤反解析为 ``PlanStepSpec``。"""
    specs: list[PlanStepSpec] = []
    for item in steps:
        specs.append(
            PlanStepSpec(
                description=str(item.get("description", "")),
                agent_role=AgentRole.from_value(str(item.get("agent_role", ""))),
            )
        )
    return specs
