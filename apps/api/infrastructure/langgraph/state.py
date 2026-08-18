"""LangGraph 状态定义：agent 循环的共享状态。"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """agent 图的状态（运行时快照，领域 ``AgentTask`` 仍为权威来源）。"""

    goal: str
    task_id: str
    messages: Annotated[list[BaseMessage], operator.add]
    plan_steps: list[dict[str, Any]]
    current_step_index: int
    memory_context: str
    plan: str
    reflection: str
    result: dict[str, Any]
    iteration: int
    max_iterations: int

    # 与任务生命周期同步
    agent_task_status: str
    waiting_agent_role: str | None
    waiting_question: str | None
    user_reply: str | None
    last_step_result: dict[str, Any] | None
    replan_enabled: bool
    use_llm_planning: bool
    summary: dict[str, Any] | None
    error: str | None
    resume_step: bool
