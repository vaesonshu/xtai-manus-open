"""Mock 搜索引擎：返回结构化占位结果，便于开发与测试。"""

from __future__ import annotations

from domain.tool.result import ToolResult


class MockSearchEngine:
    """离线搜索引擎实现。"""

    async def search_web(
        self,
        query: str,
        *,
        date_range: str | None = None,
    ) -> ToolResult:
        del date_range
        snippet = (
            f"关于「{query}」的模拟搜索结果："
            "当前为离线模式，请配置真实 SearchEngine 以获取网络数据。"
        )
        return ToolResult(
            success=True,
            message=snippet,
            data={
                "query": query,
                "results": [
                    {"title": f"{query} - 结果 1", "url": "https://example.com/1"},
                    {"title": f"{query} - 结果 2", "url": "https://example.com/2"},
                ],
            },
        )
