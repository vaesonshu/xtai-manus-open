"""search_web 工具注册测试。"""

from __future__ import annotations

import pytest

from domain.event.tool_content import build_tool_content
from infrastructure.search.mock_search_engine import MockSearchEngine
from infrastructure.tools import ToolRegistry, build_search_toolkit


def test_search_web_schema_is_registered() -> None:
    registry = ToolRegistry([build_search_toolkit(MockSearchEngine())])
    schemas = registry.get_schemas(("search_web",))
    names = [schema["function"]["name"] for schema in schemas]

    assert names == ["search_web"]


@pytest.mark.asyncio
async def test_search_web_invoke_preserves_structured_results() -> None:
    """LangChain 工具返回 JSON 字符串后，仍需还原 data.results 供前端列表渲染。"""
    toolkit = build_search_toolkit(MockSearchEngine())
    result = await toolkit.invoke("search_web", {"query": "北京旅游"})

    assert result.success is True
    assert result.data is not None
    assert result.data["query"] == "北京旅游"
    assert len(result.data["results"]) == 2

    content = build_tool_content("search_web", {"query": "北京旅游"}, result)
    assert content is not None
    assert content["type"] == "search"
    assert len(content["items"]) == 2
    assert content["items"][0]["title"] == "北京旅游 - 结果 1"
    assert content["items"][0]["url"] == "https://example.com/1"
