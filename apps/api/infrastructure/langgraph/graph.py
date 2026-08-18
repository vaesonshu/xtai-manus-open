"""LangGraph agent 图构建：init → plan → 逐步执行 → 汇总。"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from infrastructure.config import Settings
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes import (
    make_after_step_node,
    make_begin_step_node,
    make_complete_task_node,
    make_execute_step_node,
    make_fail_task_node,
    make_init_task_node,
    make_plan_node,
    make_replan_node,
    make_resume_step_node,
    make_summarize_node,
    make_wait_interrupt_node,
)
from infrastructure.langgraph.nodes.routing import (
    make_route_after_step,
    make_route_dispatch,
    route_after_execute,
)
from infrastructure.langgraph.state import AgentState


def build_agent_graph(
    settings: Settings,
    *,
    node_deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """构建并编译多 Agent 任务状态图。"""
    graph = StateGraph(AgentState)

    graph.add_node("init_task", make_init_task_node(node_deps, emitter))
    graph.add_node("plan", make_plan_node(node_deps, emitter))
    graph.add_node("begin_step", make_begin_step_node(node_deps, emitter))
    graph.add_node("execute_step", make_execute_step_node(node_deps, emitter))
    graph.add_node("wait_interrupt", make_wait_interrupt_node(node_deps, emitter))
    graph.add_node("resume_step", make_resume_step_node(node_deps, emitter))
    graph.add_node("after_step", make_after_step_node(node_deps, emitter))
    graph.add_node("replan", make_replan_node(node_deps, emitter))
    graph.add_node("summarize", make_summarize_node(node_deps, emitter))
    graph.add_node("complete_task", make_complete_task_node(node_deps, emitter))
    graph.add_node("fail_task", make_fail_task_node(node_deps, emitter))

    graph.set_entry_point("init_task")
    graph.add_edge("init_task", "plan")
    graph.add_conditional_edges(
        "plan",
        make_route_dispatch(node_deps),
        {
            "begin_step": "begin_step",
            "summarize": "summarize",
            "fail_task": "fail_task",
        },
    )
    graph.add_edge("begin_step", "execute_step")
    graph.add_conditional_edges(
        "execute_step",
        route_after_execute,
        {
            "wait_interrupt": "wait_interrupt",
            "after_step": "after_step",
            "fail_task": "fail_task",
        },
    )
    graph.add_edge("wait_interrupt", "resume_step")
    graph.add_edge("resume_step", "execute_step")
    graph.add_conditional_edges(
        "after_step",
        make_route_after_step(node_deps),
        {
            "replan": "replan",
            "dispatch": "dispatch",
            "fail_task": "fail_task",
        },
    )

    # dispatch 为虚拟路由节点：复用 plan 后的条件判断
    graph.add_node("dispatch", lambda state: state)
    graph.add_conditional_edges(
        "dispatch",
        make_route_dispatch(node_deps),
        {
            "begin_step": "begin_step",
            "summarize": "summarize",
            "fail_task": "fail_task",
        },
    )
    graph.add_edge("replan", "dispatch")
    graph.add_edge("summarize", "complete_task")
    graph.add_edge("complete_task", END)
    graph.add_edge("fail_task", END)

    return graph.compile(checkpointer=checkpointer)
