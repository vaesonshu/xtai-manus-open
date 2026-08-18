"""LangGraph 条件路由（闭包注入仓储）。"""

from __future__ import annotations

from domain.task.identifiers import TaskId
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.state import AgentState


def make_route_dispatch(deps: GraphNodeDependencies):
    """是否还有待执行步骤。"""

    def route_dispatch(state: AgentState) -> str:
        if state.get("error"):
            return "fail_task"
        task_id = TaskId(state["task_id"])
        agent_task = deps.task_repository.get(task_id)
        if agent_task is None or agent_task.plan is None:
            return "summarize"
        if agent_task.plan.get_next_step() is not None:
            return "begin_step"
        return "summarize"

    return route_dispatch


def route_after_execute(state: AgentState) -> str:
    """单步执行后的分支。"""
    if state.get("waiting_question"):
        return "wait_interrupt"
    if state.get("error"):
        return "fail_task"
    return "after_step"


def make_route_after_step(deps: GraphNodeDependencies):
    """步骤完成后是否重规划。"""

    def route_after_step(state: AgentState) -> str:
        if state.get("error"):
            return "fail_task"
        if not state.get("replan_enabled") or not state.get("use_llm_planning"):
            return "dispatch"
        task_id = TaskId(state["task_id"])
        agent_task = deps.task_repository.get(task_id)
        if agent_task is None or agent_task.plan is None:
            return "dispatch"
        if agent_task.plan.get_next_step() is not None:
            return "replan"
        return "dispatch"

    return route_after_step
