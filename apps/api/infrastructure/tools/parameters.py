"""工具参数过滤：剔除 LLM 幻觉产生的无效字段。"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool


def filter_callable_parameters(
    func: Callable[..., Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """仅保留目标可调用对象签名中存在的参数，过滤 LLM 幻觉字段。"""
    signature = inspect.signature(func)
    return {
        key: value
        for key, value in arguments.items()
        if key in signature.parameters
    }


def resolve_tool_callable(tool: BaseTool) -> Callable[..., Any]:
    """解析 LangChain Tool 背后的实际可调用对象。"""
    if tool.coroutine is not None:
        return tool.coroutine
    if tool.func is not None:
        return tool.func
    raise ValueError(f"工具[{tool.name}]缺少可调用实现")


def filter_tool_arguments(tool: BaseTool, arguments: dict[str, Any]) -> dict[str, Any]:
    """过滤传给 LangChain Tool 的参数字典。"""
    return filter_callable_parameters(resolve_tool_callable(tool), arguments)
