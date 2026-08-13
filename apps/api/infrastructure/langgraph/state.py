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
    messages: Annotated[list[BaseMessage], operator.add]
    plan: str
    reflection: str
    result: dict[str, Any]
    iteration: int
    max_iterations: int
