"""内存消息队列：测试或无 Redis 场景的轻量实现。"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from collections.abc import AsyncGenerator
from typing import Any

from infrastructure.message_queue.serialization import decode_message, encode_message


class InMemoryMessageQueue:
    """基于 deque 的内存消息队列，实现 ``MessageQueuePort`` 语义。"""

    def __init__(self) -> None:
        self._messages: deque[tuple[str, str]] = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, message: Any) -> str:
        message_id = str(uuid.uuid4())
        async with self._lock:
            self._messages.append((message_id, encode_message(message)))
        self._not_empty.set()
        return message_id

    async def get(
        self,
        start_id: str | None = None,
        block_ms: int | None = None,
    ) -> tuple[str | None, Any]:
        """按游标读取；``block_ms`` 大于 0 时在队列空时短暂阻塞。"""
        deadline = time.monotonic() + (block_ms or 0) / 1000
        while True:
            result = await self._try_get(start_id)
            if result[0] is not None:
                return result
            if not block_ms:
                return None, None
            if time.monotonic() >= deadline:
                return None, None
            self._not_empty.clear()
            try:
                await asyncio.wait_for(
                    self._not_empty.wait(),
                    timeout=min(0.1, deadline - time.monotonic()),
                )
            except TimeoutError:
                continue

    async def _try_get(
        self,
        start_id: str | None,
    ) -> tuple[str | None, Any]:
        async with self._lock:
            if not self._messages:
                return None, None

            if start_id is None:
                message_id, payload = self._messages[0]
                return message_id, decode_message(payload)

            for index, (message_id, payload) in enumerate(self._messages):
                if message_id == start_id and index + 1 < len(self._messages):
                    next_id, next_payload = self._messages[index + 1]
                    return next_id, decode_message(next_payload)
            return None, None

    async def pop(self) -> tuple[str | None, Any]:
        async with self._lock:
            if not self._messages:
                return None, None
            message_id, payload = self._messages.popleft()
            if not self._messages:
                self._not_empty.clear()
            return message_id, decode_message(payload)

    async def clear(self) -> None:
        async with self._lock:
            self._messages.clear()
        self._not_empty.clear()

    async def is_empty(self) -> bool:
        async with self._lock:
            return len(self._messages) == 0

    async def size(self) -> int:
        async with self._lock:
            return len(self._messages)

    async def delete_message(self, message_id: str) -> bool:
        async with self._lock:
            for index, (current_id, _) in enumerate(self._messages):
                if current_id == message_id:
                    del self._messages[index]
                    if not self._messages:
                        self._not_empty.clear()
                    return True
            return False

    async def get_range(
        self,
        start_id: str = "-",
        end_id: str = "+",
        count: int = 100,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """批量读取队列消息（SSE 回放）。"""
        del start_id, end_id
        async with self._lock:
            items = list(self._messages)[:count]
        for message_id, payload in items:
            yield message_id, decode_message(payload)

    async def get_latest_id(self) -> str:
        """获取最新消息 ID，空队列返回 ``0``。"""
        async with self._lock:
            if not self._messages:
                return "0"
            return self._messages[-1][0]
