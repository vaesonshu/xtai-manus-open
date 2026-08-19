"""tool_content 构建逻辑测试。"""

from __future__ import annotations

from domain.event.tool_content import build_tool_content
from domain.tool.result import ToolResult


def test_build_browser_tool_content_from_screenshot() -> None:
    result = ToolResult(
        success=True,
        message="page loaded",
        data={"screenshot": "abc123"},
    )
    content = build_tool_content("browser_view", {}, result)
    assert content is not None
    assert content["type"] == "browser"
    assert content["screenshot"] == "abc123"


def test_build_browser_tool_content_fallback_to_message() -> None:
    result = ToolResult(success=True, message="Example Domain")
    content = build_tool_content("browser_navigate", {"url": "https://example.com"}, result)
    assert content == {
        "type": "browser",
        "content": "Example Domain",
        "success": True,
    }


def test_build_file_read_tool_content() -> None:
    result = ToolResult(
        success=True,
        message="file body",
        data={"filepath": "/workspace/a.txt"},
    )
    content = build_tool_content("read_file", {"filepath": "a.txt"}, result)
    assert content == {
        "type": "file",
        "operation": "read",
        "path": "a.txt",
        "content": "file body",
        "success": True,
    }


def test_build_file_write_tool_content() -> None:
    result = ToolResult(success=True, message="written: out.md")
    content = build_tool_content(
        "write_file",
        {"filepath": "out.md", "content": "# hi"},
        result,
    )
    assert content == {
        "type": "file",
        "operation": "write",
        "path": "out.md",
        "content": "written: out.md",
        "success": True,
    }


def test_build_tool_content_returns_none_for_unsupported_tool() -> None:
    result = ToolResult(success=True, message="42")
    assert build_tool_content("calculate", {"expression": "1+1"}, result) is None
