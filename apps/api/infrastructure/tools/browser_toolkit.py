"""浏览器工具集：页面查看与导航（依赖 BrowserPort 实现）。"""

from __future__ import annotations

from langchain_core.tools import tool

from domain.ports.browser import BrowserPort
from infrastructure.tools.langchain_toolkit import LangChainToolKit


def build_browser_toolkit(browser: BrowserPort) -> LangChainToolKit:
    """构建浏览器工具集。"""

    @tool
    async def browser_view() -> str:
        """查看当前浏览器页面内容。"""
        result = await browser.view_page()
        return result.to_tool_content()

    @tool
    async def browser_navigate(url: str) -> str:
        """将浏览器导航至指定 URL。"""
        result = await browser.navigate(url)
        return result.to_tool_content()

    return LangChainToolKit(name="browser", tools=[browser_view, browser_navigate])
