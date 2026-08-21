"""工具事件扩展内容：供前端工作区富展示（浏览器截图、文件预览等）。"""

from __future__ import annotations

from typing import Any

from domain.tool.result import ToolResult

# 浏览器类工具
_BROWSER_FUNCTIONS = frozenset({"browser_view", "browser_navigate"})

# 文件读取类工具（展示文件内容）
_FILE_READ_FUNCTIONS = frozenset({"read_file"})

# 文件写入类工具（展示路径与操作结果）
_FILE_WRITE_FUNCTIONS = frozenset({"write_file", "replace_in_file"})

# 网络搜索类工具（结构化结果列表）
_SEARCH_FUNCTIONS = frozenset(
    {"search_web", "search_web_zh", "search_web_en", "duckduckgo_search"}
)


def build_tool_content(
    function_name: str,
    function_args: dict[str, Any],
    result: ToolResult,
) -> dict[str, Any] | None:
    """根据工具名与 ``ToolResult`` 构建结构化 ``tool_content``。

    返回 ``None`` 表示无富展示内容，前端回退到 ``function_result`` 解析。
    """
    data = result.data or {}

    if function_name in _BROWSER_FUNCTIONS:
        return _build_browser_content(function_args, result, data)

    if function_name in _FILE_READ_FUNCTIONS:
        return _build_file_read_content(function_args, result, data)

    if function_name in _FILE_WRITE_FUNCTIONS:
        return _build_file_write_content(function_name, function_args, result, data)

    if function_name in _SEARCH_FUNCTIONS:
        return _build_search_content(function_args, result, data)

    return None


def _build_browser_content(
    function_args: dict[str, Any],
    result: ToolResult,
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """浏览器工具：截图优先；否则下发 url/title/正文，供前端页面预览。"""
    screenshot = data.get("screenshot")
    url = str(data.get("url") or function_args.get("url") or "").strip()
    title = str(data.get("title") or "").strip()
    # 正文取 data.content，避免把「已打开: …」拼装稿当页面内容
    page_text = str(data.get("content") or "").strip()

    if screenshot:
        payload: dict[str, Any] = {
            "type": "browser",
            "screenshot": str(screenshot),
            "success": result.success,
        }
        if url:
            payload["url"] = url
        if title:
            payload["title"] = title
        return payload

    content = page_text or (result.message or "").strip()
    if not content:
        return None

    return {
        "type": "browser",
        "success": result.success,
        "url": url,
        "title": title,
        "content": content,
    }


def _build_file_read_content(
    function_args: dict[str, Any],
    result: ToolResult,
    data: dict[str, Any],
) -> dict[str, Any]:
    """读取文件：向前端提供路径与文件正文。"""
    filepath = function_args.get("filepath") or data.get("filepath") or ""
    return {
        "type": "file",
        "operation": "read",
        "path": str(filepath),
        "content": result.message if result.success else "",
        "success": result.success,
    }


def _build_file_write_content(
    function_name: str,
    function_args: dict[str, Any],
    result: ToolResult,
    data: dict[str, Any],
) -> dict[str, Any]:
    """写入/替换文件：展示目标路径与操作结果摘要。"""
    filepath = function_args.get("filepath") or data.get("filepath") or ""
    operation = "write" if function_name == "write_file" else "replace"
    return {
        "type": "file",
        "operation": operation,
        "path": str(filepath),
        "content": result.message,
        "success": result.success,
    }


def _build_search_content(
    function_args: dict[str, Any],
    result: ToolResult,
    data: dict[str, Any],
) -> dict[str, Any]:
    """搜索工具：向前端提供可渲染的结果列表（标题/链接/摘要）。"""
    raw_results = data.get("results")
    items: list[dict[str, str]] = []
    if isinstance(raw_results, list):
        for entry in raw_results:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "").strip()
            url = str(entry.get("url") or "").strip()
            snippet = str(entry.get("snippet") or "").strip()
            if not title and not url and not snippet:
                continue
            items.append(
                {
                    "title": title or "无标题",
                    "url": url,
                    "snippet": snippet,
                }
            )

    query = str(data.get("query") or function_args.get("query") or "").strip()
    provider = str(data.get("provider") or "baidu").strip()

    return {
        "type": "search",
        "success": result.success,
        "content": result.message,
        "query": query,
        "provider": provider,
        "items": items,
    }
