"""JSON 解析端口：修复并解析 LLM 输出的 JSON 文本。"""

from __future__ import annotations

from typing import Any, Protocol


class JsonParserPort(Protocol):
    """JSON 解析器端口。"""

    async def invoke(
        self,
        text: str,
        *,
        default_value: Any | None = None,
    ) -> Any:
        """解析 JSON 文本；失败时返回 default_value 或抛出异常。"""
        ...
