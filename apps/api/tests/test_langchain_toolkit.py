"""LangChain 工具适配器测试。"""

from __future__ import annotations

import pytest
from langchain_core.tools import tool

from domain.tool.result import ToolResult
from infrastructure.tools.langchain_toolkit import LangChainToolKit
from infrastructure.tools.mock_tool import build_mock_toolkit
from infrastructure.tools.parameters import filter_callable_parameters, filter_tool_arguments


@tool
def add(a: int, b: int, noise: str = "") -> str:
    """两数相加（noise 为 LLM 幻觉字段，应被过滤）。"""
    del noise
    return str(a + b)


@pytest.mark.asyncio
async def test_langchain_toolkit_invoke_echo() -> None:
    toolkit = build_mock_toolkit()
    result = await toolkit.invoke("echo", {"text": "hello"})
    assert result.success is True
    assert result.message == "hello"


@pytest.mark.asyncio
async def test_langchain_toolkit_filters_hallucinated_arguments() -> None:
    toolkit = LangChainToolKit(name="math", tools=[add])
    result = await toolkit.invoke(
        "add",
        {"a": 2, "b": 3, "unexpected_field": "x"},
    )
    assert result.success is True
    assert result.message == "5"


def test_filter_callable_parameters() -> None:
    def sample(x: int, y: str) -> None:
        del x, y

    filtered = filter_callable_parameters(
        sample,
        {"x": 1, "y": "ok", "z": "drop"},
    )
    assert filtered == {"x": 1, "y": "ok"}


def test_filter_tool_arguments_on_langchain_tool() -> None:
    filtered = filter_tool_arguments(add, {"a": 1, "b": 2, "noise": "x", "extra": 1})
    assert filtered == {"a": 1, "b": 2, "noise": "x"}
