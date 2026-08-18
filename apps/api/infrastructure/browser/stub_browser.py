"""Stub 浏览器实现：预留接口，后续可接入 Playwright 等。"""

from __future__ import annotations

from domain.tool.result import ToolResult


class StubBrowser:
    """占位浏览器，返回未实现提示。"""

    async def view_page(self) -> ToolResult:
        return ToolResult(success=False, message="browser automation is not configured")

    async def navigate(self, url: str) -> ToolResult:
        return ToolResult(success=False, message=f"browser navigate not configured: {url}")
