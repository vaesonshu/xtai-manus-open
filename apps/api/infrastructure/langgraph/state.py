"""LangGraph 状态定义：agent 循环的共享状态。

``TypedDict`` 作为 StateGraph 的状态契约，节点通过 ``Annotated`` 累加器
定义字段的合并语义（例如 messages 用 ``operator.add`` 追加）。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """agent 图的状态。"""

    goal: str
    task_id: str
    messages: Annotated[list[BaseMessage], operator.add]
    # 结构化多 Agent 规划（与领域 TaskPlan 对应）
    plan_steps: list[dict[str, Any]]
    current_step_index: int
    # 记忆上下文（由 MemoryApplicationService 拼装）
    memory_context: str
    plan: str
    reflection: str
    result: dict[str, Any]
    iteration: int
    max_iterations: int
