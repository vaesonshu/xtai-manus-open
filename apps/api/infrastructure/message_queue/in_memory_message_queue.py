"""内存消息队列：测试或无 Redis 场景的轻量实现。"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from typing import Any

from infrastructure.message_queue.serialization import decode_message, encode_message


class InMemoryMessageQueue:
    """基于 deque 的内存消息队列，实现 ``MessageQueuePort`` 语义。"""

    def __init__(self) -> None:
        self._messages: deque[tuple[str, str]] = deque()
        self._lock = asyncio.Lock()

    async def put(self, message: Any) -> str:
        message_id = str(uuid.uuid4())
        async with self._lock:
            self._messages.append((message_id, encode_message(message)))
        return message_id

    async def get(
        self,
        start_id: str | None = None,
        block_ms: int | None = None,
    ) -> tuple[str | None, Any]:
        del block_ms  # 内存实现无需阻塞等待
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
            return message_id, decode_message(payload)

    async def clear(self) -> None:
        async with self._lock:
            self._messages.clear()

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
                    return True
            return False
