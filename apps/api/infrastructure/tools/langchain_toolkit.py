"""LangChain Tool 适配器：将 LangChain 工具集实现为 ``ToolPort``。"""

from __future__ import annotations

import json
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
            return _coerce_tool_result(raw_result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("LangChain 工具调用失败: %s", function_name)
            return ToolResult(success=False, message=str(exc))


def _coerce_tool_result(raw_result: Any) -> ToolResult:
    """将 LangChain 工具返回值还原为 ``ToolResult``。

    多数工具通过 ``ToolResult.to_tool_content()`` 返回 JSON 字符串。
    若原样塞进 ``message``，``data.results`` 等结构化字段会丢失，
    前端就只能把整段 JSON 当纯文本展示。
    """
    if isinstance(raw_result, ToolResult):
        return raw_result

    if isinstance(raw_result, dict):
        parsed = _payload_to_tool_result(raw_result)
        if parsed is not None:
            return parsed
        return ToolResult(
            success=True,
            message=str(raw_result),
            data={"result": raw_result},
        )

    if isinstance(raw_result, str):
        parsed = _parse_tool_payload(raw_result)
        if parsed is not None:
            return parsed
        return ToolResult(success=True, message=raw_result)

    return ToolResult(
        success=True,
        message=str(raw_result),
        data={"result": raw_result},
    )


def _parse_tool_payload(raw: str) -> ToolResult | None:
    """尝试把 ``to_tool_content()`` JSON 还原为 ToolResult。"""
    trimmed = raw.strip()
    if not trimmed.startswith("{") and not trimmed.startswith("["):
        return None
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return _payload_to_tool_result(payload)


def _payload_to_tool_result(payload: dict[str, Any]) -> ToolResult | None:
    """仅识别带 success 字段的工具载荷，避免误解析普通 JSON。"""
    if "success" not in payload:
        return None
    data = payload.get("data")
    return ToolResult(
        success=bool(payload.get("success")),
        message=str(payload.get("message") or ""),
        data=data if isinstance(data, dict) else None,
    )
