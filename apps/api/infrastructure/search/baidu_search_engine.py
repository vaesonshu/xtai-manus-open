"""百度搜索引擎：通过 HTTP 抓取 SERP 并解析结构化结果。"""

from __future__ import annotations

import logging

import httpx

from domain.tool.result import ToolResult
from infrastructure.search.baidu_parser import (
    format_search_message,
    looks_like_captcha_page,
    parse_baidu_search_html,
)

logger = logging.getLogger(__name__)

_BAIDU_SEARCH_URL = "https://www.baidu.com/s"
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.baidu.com/",
}


class BaiduSearchEngine:
    """基于百度搜索页的自研搜索引擎实现。"""

    def __init__(
        self,
        *,
        max_results: int = 8,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._max_results = max(1, min(max_results, 20))
        self._timeout = timeout_seconds

    async def search_web(
        self,
        query: str,
        *,
        date_range: str | None = None,
    ) -> ToolResult:
        """调用百度搜索并返回结构化 ToolResult。"""
        del date_range  # 百度时间筛选参数复杂，当前版本暂不映射
        normalized_query = query.strip()
        if not normalized_query:
            return ToolResult(success=False, message="搜索关键词不能为空")

        params = {
            "wd": normalized_query,
            "rn": str(self._max_results),
            "ie": "utf-8",
        }

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self._timeout,
                headers=_DEFAULT_HEADERS,
            ) as client:
                response = await client.get(_BAIDU_SEARCH_URL, params=params)
                response.raise_for_status()
                page_html = response.text
        except httpx.HTTPError as exc:
            logger.exception("百度搜索请求失败: query=%s", normalized_query)
            return ToolResult(
                success=False,
                message=f"百度搜索请求失败: {exc}",
                data={"query": normalized_query, "results": []},
            )

        if looks_like_captcha_page(page_html):
            return ToolResult(
                success=False,
                message="百度搜索触发风控验证，请稍后重试或更换网络环境。",
                data={"query": normalized_query, "results": []},
            )

        results = parse_baidu_search_html(page_html, max_results=self._max_results)
        message = format_search_message(normalized_query, results)
        return ToolResult(
            success=True,
            message=message,
            data={
                "query": normalized_query,
                "provider": "baidu",
                "results": results,
            },
        )
