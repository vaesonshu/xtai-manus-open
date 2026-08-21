"""搜索工具集：网络搜索能力。"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from domain.ports.search_engine import SearchEnginePort
from infrastructure.tools.langchain_toolkit import LangChainToolKit


def build_search_toolkit(search_engine: SearchEnginePort) -> LangChainToolKit:
    """构建搜索工具集。"""

    @tool
    async def search_web(query: str, date_range: Optional[str] = None) -> str:
        """使用百度搜索引擎检索实时信息。适用于事实核查、新闻、文档与公开资料查询。"""
        result = await search_engine.search_web(query, date_range=date_range)
        return result.to_tool_content()

    return LangChainToolKit(name="search", tools=[search_web])
