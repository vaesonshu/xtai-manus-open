"""搜索引擎端口。"""

from __future__ import annotations

from typing import Protocol

from domain.tool.result import ToolResult


class SearchEnginePort(Protocol):
    """Web 搜索抽象端口。"""

    async def search_web(
        self,
        query: str,
        *,
        date_range: str | None = None,
    ) -> ToolResult:
        """执行网络搜索并返回结果。"""
        ...
