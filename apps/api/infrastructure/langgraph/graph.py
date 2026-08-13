"""LangGraph agent 图构建：plan → execute → reflect 循环 + 边界条件。"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from infrastructure.config import Settings
from infrastructure.langgraph.state import AgentState


def should_continue(state: AgentState) -> str:
    """边界条件：达到最大迭代数则结束，否则继续反思/执行循环。"""
    if state.get("iteration", 0) >= state.get("max_iterations", 1):
        return "end"
    return "reflect"


def build_agent_graph(settings: Settings) -> CompiledStateGraph:
    """构建并编译 agent 状态图。

    图结构：``planner → executor → reflect``，reflect 后按边界条件决定
    继续或结束。真实节点实现见 ``nodes.py``。
    """
    from infrastructure.langgraph.nodes import (
        executor_node,
        planner_node,
        reflector_node,
    )

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("reflect", reflector_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reflect")
    graph.add_conditional_edges("reflect", should_continue, {"reflect": "executor", "end": END})

    return graph.compile()
