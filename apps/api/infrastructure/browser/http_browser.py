"""HTTP 轻量浏览器：抓取网页并提取可读正文（无需 Playwright）。"""

from __future__ import annotations

import html
import logging
import re
from urllib.parse import urlparse

import httpx

from domain.tool.result import ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _strip_html_tags(raw: str) -> str:
    """移除 HTML 标签并规范化空白。"""
    text = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _extract_title(page_html: str) -> str:
    match = re.search(r"<title[^>]*>([\s\S]*?)</title>", page_html, re.I)
    return _strip_html_tags(match.group(1)) if match else ""


def _extract_readable_text(page_html: str) -> str:
    """从 HTML 提取正文文本，去掉 script/style。"""
    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", page_html, flags=re.I)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
    body_match = re.search(r"<body[\s\S]*?</body>", cleaned, re.I)
    chunk = body_match.group(0) if body_match else cleaned
    return _strip_html_tags(chunk)


def _validate_http_url(url: str) -> str | None:
    """校验 URL，仅允许 http/https。"""
    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


class HttpBrowser:
    """基于 httpx 的轻量浏览器，维护当前页面状态供 view/navigate 使用。"""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_content_chars: int = 12000,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_content_chars = max(1000, max_content_chars)
        self._current_url: str | None = None
        self._current_title: str = ""
        self._current_text: str = ""

    async def navigate(self, url: str) -> ToolResult:
        """抓取指定 URL 并缓存为当前页面。"""
        normalized = _validate_http_url(url)
        if normalized is None:
            return ToolResult(success=False, message=f"无效的 URL: {url}")

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self._timeout,
                headers=_DEFAULT_HEADERS,
            ) as client:
                response = await client.get(normalized)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return ToolResult(
                        success=False,
                        message=f"当前仅支持 HTML 页面，实际 Content-Type: {content_type}",
                        data={"url": normalized},
                    )
                page_html = response.text
        except httpx.HTTPError as exc:
            logger.exception("browser navigate failed: %s", normalized)
            return ToolResult(
                success=False,
                message=f"页面打开失败: {exc}",
                data={"url": normalized},
            )

        title = _extract_title(page_html)
        text = _extract_readable_text(page_html)
        if len(text) > self._max_content_chars:
            text = f"{text[: self._max_content_chars]}\n...(内容已截断)"

        self._current_url = normalized
        self._current_title = title
        self._current_text = text

        heading = title or normalized
        message = f"已打开: {heading}\nURL: {normalized}\n\n{text or '(页面无可见文本，可能需 JavaScript 渲染)'}"
        return ToolResult(
            success=True,
            message=message,
            data={
                "url": normalized,
                "title": title,
                "content": text,
            },
        )

    async def view_page(self) -> ToolResult:
        """返回当前已打开页面的正文。"""
        if not self._current_url:
            return ToolResult(
                success=False,
                message="当前没有打开的页面，请先调用 browser_navigate",
            )

        heading = self._current_title or self._current_url
        message = f"当前页面: {heading}\nURL: {self._current_url}\n\n{self._current_text or '(无可见文本)'}"
        return ToolResult(
            success=True,
            message=message,
            data={
                "url": self._current_url,
                "title": self._current_title,
                "content": self._current_text,
            },
        )
