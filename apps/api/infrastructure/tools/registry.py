"""工具注册表：按名称聚合工具集并解析 function 调用。"""

from __future__ import annotations

from typing import Any

from domain.ports.tool import ToolPort
from domain.tool.result import ToolResult


class ToolRegistry:
    """管理多个 ``ToolPort`` 实现，供 ReAct 执行器使用。"""

    def __init__(self, tools: list[ToolPort] | None = None) -> None:
        self._tools: list[ToolPort] = list(tools or [])
        self._index: dict[str, ToolPort] = {}
        self._rebuild_index()

    def register(self, tool: ToolPort) -> None:
        """注册一个工具集。"""
        self._tools.append(tool)
        self._rebuild_index()

    def get_schemas(self, tool_names: tuple[str, ...]) -> list[dict[str, Any]]:
        """按 function 名收集 schema（与 role_config.tool_names 对齐）。"""
        if not tool_names:
            return []

        allowed = set(tool_names)
        schemas: list[dict[str, Any]] = []
        for tool in self._tools:
            for schema in tool.get_schemas():
                function = schema.get("function", {})
                name = function.get("name")
                if name and name in allowed:
                    schemas.append(schema)
        return schemas

    def resolve(self, function_name: str) -> ToolPort:
        """根据 function 名定位所属工具集。"""
        tool = self._index.get(function_name)
        if tool is None:
            raise ValueError(f"未知工具: {function_name}")
        return tool

    async def invoke(self, function_name: str, arguments: dict[str, Any]) -> ToolResult:
        """调用指定 function 工具。"""
        tool = self.resolve(function_name)
        return await tool.invoke(function_name, arguments)

    def _rebuild_index(self) -> None:
        self._index.clear()
        for tool in self._tools:
            for schema in tool.get_schemas():
                function = schema.get("function", {})
                name = function.get("name")
                if name:
                    self._index[name] = tool
