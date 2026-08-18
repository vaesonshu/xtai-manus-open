"""Mock 工具集：基于 LangChain ``@tool`` 的测试用工具。"""

from __future__ import annotations

from langchain_core.tools import tool

from infrastructure.tools.langchain_toolkit import LangChainToolKit


@tool
def echo(text: str) -> str:
    """回显输入文本，用于测试工具调用链路。"""
    normalized = text.strip()
    return normalized or "(empty)"


def build_mock_toolkit() -> LangChainToolKit:
    """构建 mock 工具集（供容器与测试使用）。"""
    return LangChainToolKit(name="mock", tools=[echo])
