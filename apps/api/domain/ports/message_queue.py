"""消息队列端口：Task 输入/输出流与 SSE 事件通道的抽象。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Protocol


class MessageQueuePort(Protocol):
    """消息队列协议。

    用于 Task 的 input/output 流，解耦领域模型与 Redis Stream 等实现。
    """

    async def put(self, message: Any) -> str:
        """写入一条消息，返回消息 ID。"""
        ...

    async def get(
        self,
        start_id: str | None = None,
        block_ms: int | None = None,
    ) -> tuple[str | None, Any]:
        """按游标读取一条消息（可阻塞等待）。"""
        ...

    async def pop(self) -> tuple[str | None, Any]:
        """读取并移除队列首条消息。"""
        ...

    async def clear(self) -> None:
        """清空队列。"""
        ...

    async def is_empty(self) -> bool:
        """队列是否为空。"""
        ...

    async def size(self) -> int:
        """队列长度。"""
        ...

    async def delete_message(self, message_id: str) -> bool:
        """按消息 ID 删除指定消息。"""
        ...

    async def get_range(
        self,
        start_id: str = "-",
        end_id: str = "+",
        count: int = 100,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """批量读取区间消息（SSE 回放等场景）。"""
        ...

    async def get_latest_id(self) -> str:
        """获取最新消息 ID，空队列返回 ``0``。"""
        ...
