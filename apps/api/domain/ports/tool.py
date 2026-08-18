"""工具端口：Agent ReAct 循环与具体工具实现之间的抽象。"""

from __future__ import annotations

from typing import Any, Protocol

from domain.tool.result import ToolResult


class ToolPort(Protocol):
    """工具集端口：一个实现可暴露多个 function tool。"""

    @property
    def name(self) -> str:
        """工具集名称（用于事件展示）。"""
        ...

    def get_schemas(self) -> list[dict[str, Any]]:
        """返回 OpenAI function calling 格式的工具声明列表。"""
        ...

    def has_tool(self, function_name: str) -> bool:
        """是否包含指定函数工具。"""
        ...

    async def invoke(self, function_name: str, arguments: dict[str, Any]) -> ToolResult:
        """调用工具并返回结构化结果。"""
        ...
