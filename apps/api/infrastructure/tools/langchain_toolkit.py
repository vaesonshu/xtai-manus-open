"""LangChain Tool 适配器：将 LangChain 工具集实现为 ``ToolPort``。"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from domain.tool.result import ToolResult
from infrastructure.tools.parameters import filter_tool_arguments

logger = logging.getLogger(__name__)


class LangChainToolKit:
    """将一组 LangChain ``BaseTool`` 适配为领域 ``ToolPort`` 协议。"""

    def __init__(self, name: str, tools: list[BaseTool]) -> None:
        if not name.strip():
            raise ValueError("toolkit name must not be empty")
        if not tools:
            raise ValueError("toolkit must contain at least one tool")

        self._name = name.strip()
        self._tools: dict[str, BaseTool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"duplicate tool name in toolkit: {tool.name}")
            self._tools[tool.name] = tool
        self._schema_cache: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return self._name

    def get_schemas(self) -> list[dict[str, Any]]:
        """导出 OpenAI function calling 格式 schema。"""
        if self._schema_cache is None:
            self._schema_cache = [
                convert_to_openai_tool(tool) for tool in self._tools.values()
            ]
        return list(self._schema_cache)

    def has_tool(self, function_name: str) -> bool:
        return function_name in self._tools

    async def invoke(self, function_name: str, arguments: dict[str, Any]) -> ToolResult:
        """调用 LangChain 工具并封装为 ``ToolResult``。"""
        tool = self._tools.get(function_name)
        if tool is None:
            return ToolResult(success=False, message=f"未知工具: {function_name}")

        filtered = filter_tool_arguments(tool, arguments)
        try:
            raw_result = await tool.ainvoke(filtered)
            message = str(raw_result)
            return ToolResult(
                success=True,
                message=message,
                data={"result": raw_result},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("LangChain 工具调用失败: %s", function_name)
            return ToolResult(success=False, message=str(exc))
