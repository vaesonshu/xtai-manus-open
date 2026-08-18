"""工具执行结果值对象。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """工具调用结果，序列化后回传给 LLM。"""

    success: bool
    message: str
    data: dict[str, Any] | None = None

    def to_tool_content(self) -> str:
        """转换为 tool 角色的 message content。"""
        import json

        payload: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
        }
        if self.data is not None:
            payload["data"] = self.data
        return json.dumps(payload, ensure_ascii=False)
