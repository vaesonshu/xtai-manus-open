"""浏览器自动化端口（预留扩展）。"""

from __future__ import annotations

from typing import Protocol

from domain.tool.result import ToolResult


class BrowserPort(Protocol):
    """浏览器操作抽象端口。"""

    async def view_page(self) -> ToolResult:
        """查看当前页面内容。"""
        ...

    async def navigate(self, url: str) -> ToolResult:
        """导航到指定 URL。"""
        ...
