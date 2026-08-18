"""基于 Redis Stream 的消息队列实现。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from redis.asyncio import Redis

from infrastructure.config import get_settings
from infrastructure.message_queue.serialization import decode_message, encode_message
from infrastructure.redis.async_client import AsyncRedisClient, get_async_redis

logger = logging.getLogger(__name__)


class RedisStreamMessageQueue:
    """基于 Redis Stream 的消息队列实现。"""

    def __init__(
        self,
        stream_name: str,
        redis_client: AsyncRedisClient | None = None,
        *,
        lock_expire_seconds: int = 10,
    ) -> None:
        settings = get_settings()
        self._stream_name = f"{settings.redis_key_prefix}:{stream_name}"
        self._redis = redis_client or get_async_redis()
        self._lock_expire_seconds = lock_expire_seconds

    async def put(self, message: Any) -> str:
        """往 Stream 写入一条消息并返回 ID。"""
        logger.debug("往消息队列[%s]写入消息", self._stream_name)
        message_id = await self._redis.client.xadd(
            self._stream_name,
            {"data": encode_message(message)},
        )
        return str(message_id)

    async def get(
        self,
        start_id: str | None = None,
        block_ms: int | None = None,
    ) -> tuple[str | None, Any]:
        """按游标从 Stream 读取一条消息。"""
        cursor = start_id or "0"
        messages = await self._redis.client.xread(
            {self._stream_name: cursor},
            count=1,
            block=block_ms,
        )
        if not messages:
            return None, None

        stream_messages = messages[0][1]
        if not stream_messages:
            return None, None

        message_id, message_data = stream_messages[0]
        try:
            return str(message_id), decode_message(message_data.get("data"))
        except Exception:  # noqa: BLE001 - 单条消息解析失败不应拖垮消费者
            logger.exception("从消息队列[%s]解析消息失败", self._stream_name)
            return None, None

    async def pop(self) -> tuple[str | None, Any]:
        """弹出 Stream 首条消息（带分布式锁，避免并发重复消费）。"""
        lock_key = f"lock:{self._stream_name}:pop"
        lock_value = await self._acquire_lock(lock_key)
        if not lock_value:
            return None, None

        try:
            messages = await self._redis.client.xrange(
                self._stream_name,
                "-",
                "+",
                count=1,
            )
            if not messages:
                return None, None

            message_id, message_data = messages[0]
            await self._redis.client.xdel(self._stream_name, message_id)
            return str(message_id), decode_message(message_data.get("data"))
        except Exception:  # noqa: BLE001
            logger.exception("从消息队列[%s]弹出消息失败", self._stream_name)
            return None, None
        finally:
            await self._release_lock(lock_key, lock_value)

    async def clear(self) -> None:
        """清空 Stream。"""
        await self._redis.client.xtrim(self._stream_name, 0)

    async def is_empty(self) -> bool:
        return await self.size() == 0

    async def size(self) -> int:
        return int(await self._redis.client.xlen(self._stream_name))

    async def delete_message(self, message_id: str) -> bool:
        try:
            await self._redis.client.xdel(self._stream_name, message_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def get_range(
        self,
        start_id: str = "-",
        end_id: str = "+",
        count: int = 100,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """批量读取 Stream 区间消息（SSE 回放等场景）。"""
        messages = await self._redis.client.xrange(
            self._stream_name,
            start_id,
            end_id,
            count=count,
        )
        for message_id, message_data in messages:
            try:
                yield str(message_id), decode_message(message_data.get("data"))
            except Exception:  # noqa: BLE001
                continue

    async def get_latest_id(self) -> str:
        """获取 Stream 最新消息 ID，空队列返回 ``0``。"""
        messages = await self._redis.client.xrevrange(
            self._stream_name,
            "+",
            "-",
            count=1,
        )
        if not messages:
            return "0"
        return str(messages[0][0])

    async def _acquire_lock(self, lock_key: str, timeout_seconds: float = 5.0) -> str | None:
        lock_value = str(uuid.uuid4())
        remaining = timeout_seconds
        while remaining > 0:
            acquired = await self._redis.client.set(
                lock_key,
                lock_value,
                nx=True,
                ex=self._lock_expire_seconds,
            )
            if acquired:
                return lock_value
            await asyncio.sleep(0.1)
            remaining -= 0.1
        return None

    async def _release_lock(self, lock_key: str, lock_value: str) -> bool:
        release_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        try:
            script = self._redis.client.register_script(release_script)
            result = await script(keys=[lock_key], args=[lock_value])
            return result == 1
        except Exception:  # noqa: BLE001
            return False

    def bind_redis(self, client: Redis) -> None:
        """测试注入 fakeredis 客户端。"""
        self._redis.bind_client(client)
