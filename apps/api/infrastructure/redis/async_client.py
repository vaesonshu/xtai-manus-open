"""异步 Redis 客户端：供 Redis Stream 消息队列与任务执行使用。"""

from __future__ import annotations

import logging
from functools import lru_cache

from redis.asyncio import Redis

from infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AsyncRedisClient:
    """异步 Redis 客户端，生命周期由应用 lifespan 管理。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Redis | None = None

    async def init(self) -> None:
        """建立连接并 ping 验证。"""
        if self._client is not None:
            logger.warning("异步 Redis 客户端已初始化，跳过重复操作")
            return

        self._client = Redis.from_url(
            self._settings.redis_url,
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("异步 Redis 客户端初始化成功")

    async def shutdown(self) -> None:
        """关闭连接并清理单例缓存。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("异步 Redis 客户端已关闭")
        get_async_redis.cache_clear()

    @property
    def client(self) -> Redis:
        """获取底层 redis.asyncio 客户端。"""
        if self._client is None:
            raise RuntimeError("异步 Redis 客户端未初始化，请在应用 lifespan 中调用 init()")
        return self._client

    def bind_client(self, client: Redis) -> None:
        """注入客户端（测试用 fakeredis 等）。"""
        self._client = client


@lru_cache
def get_async_redis() -> AsyncRedisClient:
    """获取异步 Redis 单例。"""
    return AsyncRedisClient()
