"""LangGraph 规划桥接测试。"""

from __future__ import annotations

from infrastructure.langgraph.planning_bridge import build_offline_plan, plan_to_state_steps
from infrastructure.langgraph.nodes import executor_node, planner_node


def test_planner_node_produces_structured_steps() -> None:
    result = planner_node({"goal": "写一份市场报告", "iteration": 0})
    assert len(result["plan_steps"]) == 3
    assert result["current_step_index"] == 0
    assert "researcher" in result["plan"]


def test_executor_node_advances_step_index() -> None:
    plan = build_offline_plan("分析竞品")
    state = {
        "goal": "分析竞品",
        "plan_steps": plan_to_state_steps(plan),
        "current_step_index": 0,
        "iteration": 0,
        "max_iterations": 5,
    }
    first = executor_node(state)
    assert first["current_step_index"] == 1
    assert "researcher" in first["messages"][-1].content
