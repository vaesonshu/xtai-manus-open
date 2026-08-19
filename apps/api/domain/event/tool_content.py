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
        return _build_browser_content(result, data)

    if function_name in _FILE_READ_FUNCTIONS:
        return _build_file_read_content(function_args, result, data)

    if function_name in _FILE_WRITE_FUNCTIONS:
        return _build_file_write_content(function_name, function_args, result, data)

    return None


def _build_browser_content(
    result: ToolResult,
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """浏览器工具：优先截图，否则回退页面文本摘要。"""
    screenshot = data.get("screenshot")
    if screenshot:
        return {
            "type": "browser",
            "screenshot": str(screenshot),
            "success": result.success,
        }

    message = (result.message or "").strip()
    if not message:
        return None

    return {
        "type": "browser",
        "content": message,
        "success": result.success,
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
