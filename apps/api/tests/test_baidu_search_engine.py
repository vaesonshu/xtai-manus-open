"""百度搜索解析与引擎测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from infrastructure.search.baidu_parser import (
    format_search_message,
    parse_baidu_search_html,
)
from infrastructure.search.baidu_search_engine import BaiduSearchEngine

SAMPLE_BAIDU_HTML = """
<body>
<div class="result c-container xpath-log new-pmd"
    id="1"
    mu="https://docs.python.org/zh-cn/3/tutorial/index.html"
>
  <h3 class="c-title"><a href="https://www.baidu.com/link?url=abc">Python 官方教程</a></h3>
  <div class="c-abstract">Python 官方中文教程，适合入门与进阶。</div>
</div>
<div class="result c-container xpath-log new-pmd"
    id="2"
    mu="https://example.com/python-guide"
>
  <h3 class="c-title"><a href="https://www.baidu.com/link?url=def">Python 入门指南</a></h3>
  <div class="c-abstract">从零开始学习 Python 编程语言。</div>
</div>
</body>
"""


def test_parse_baidu_search_html_extracts_results() -> None:
    results = parse_baidu_search_html(SAMPLE_BAIDU_HTML, max_results=5)

    assert len(results) == 2
    assert results[0]["title"] == "Python 官方教程"
    assert results[0]["url"] == "https://docs.python.org/zh-cn/3/tutorial/index.html"
    assert "官方中文教程" in results[0]["snippet"]


def test_format_search_message_contains_query_and_items() -> None:
    results = parse_baidu_search_html(SAMPLE_BAIDU_HTML, max_results=5)
    message = format_search_message("Python 教程", results)

    assert "Python 教程" in message
    assert "Python 官方教程" in message
    assert "docs.python.org" in message


@pytest.mark.asyncio
async def test_baidu_search_engine_uses_parser_on_http_response() -> None:
    engine = BaiduSearchEngine(max_results=5, timeout_seconds=5.0)
    mock_response = httpx.Response(
        200,
        text=SAMPLE_BAIDU_HTML,
        request=httpx.Request("GET", "https://www.baidu.com/s"),
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "infrastructure.search.baidu_search_engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.search_web("Python 教程")

    assert result.success is True
    assert result.data is not None
    assert result.data["provider"] == "baidu"
    assert result.data["query"] == "Python 教程"
    assert len(result.data["results"]) == 2
    assert "Python 官方教程" in result.message


@pytest.mark.asyncio
async def test_baidu_search_engine_rejects_empty_query() -> None:
    engine = BaiduSearchEngine()
    result = await engine.search_web("   ")

    assert result.success is False
    assert "不能为空" in result.message
