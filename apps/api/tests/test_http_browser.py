"""HTTP 浏览器测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from infrastructure.browser.http_browser import HttpBrowser

SAMPLE_PAGE = """
<html>
<head><title>北京旅游 - 示例页</title></head>
<body>
  <script>console.log("ignore")</script>
  <h1>欢迎访问北京</h1>
  <p>这是页面正文内容，供 Agent 阅读。</p>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_http_browser_navigate_extracts_title_and_text() -> None:
    browser = HttpBrowser(max_content_chars=5000)
    mock_response = httpx.Response(
        200,
        text=SAMPLE_PAGE,
        headers={"content-type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", "https://www.visitbeijing.com.cn/article/demo"),
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("infrastructure.browser.http_browser.httpx.AsyncClient", return_value=mock_client):
        result = await browser.navigate("https://www.visitbeijing.com.cn/article/demo")

    assert result.success is True
    assert "北京旅游" in result.message
    assert "欢迎访问北京" in result.message
    assert result.data is not None
    assert result.data["url"] == "https://www.visitbeijing.com.cn/article/demo"


@pytest.mark.asyncio
async def test_http_browser_view_page_requires_navigation() -> None:
    browser = HttpBrowser()
    result = await browser.view_page()

    assert result.success is False
    assert "browser_navigate" in result.message


@pytest.mark.asyncio
async def test_http_browser_view_page_returns_cached_content() -> None:
    browser = HttpBrowser(max_content_chars=5000)
    mock_response = httpx.Response(
        200,
        text=SAMPLE_PAGE,
        headers={"content-type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", "https://example.com"),
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("infrastructure.browser.http_browser.httpx.AsyncClient", return_value=mock_client):
        await browser.navigate("https://example.com")
        result = await browser.view_page()

    assert result.success is True
    assert "欢迎访问北京" in result.message
