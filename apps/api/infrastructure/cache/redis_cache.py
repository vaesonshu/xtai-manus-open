"""Redis 缓存适配器。"""

from __future__ import annotations

import logging

import redis

from infrastructure.config import Settings

logger = logging.getLogger(__name__)


class RedisCache:
    """基于 redis-py 的 ``CachePort`` 实现。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # decode_responses=True 使 get/set 直接处理 str，避免手动编解码
        self._client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    def get(self, key: str) -> str | None:
        return self._client.get(self._namespaced(key))

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._settings.redis_default_ttl
        self._client.set(self._namespaced(key), value, ex=ttl)

    def delete(self, key: str) -> None:
        self._client.delete(self._namespaced(key))

    def ping(self) -> bool:
        return bool(self._client.ping())

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001 - 关闭连接失败不应阻断进程退出
            logger.exception("关闭 Redis 连接失败")

    def _namespaced(self, key: str) -> str:
        """为键添加全局前缀，避免多环境/多服务键冲突。"""
        return f"{self._settings.redis_key_prefix}:{key}"
