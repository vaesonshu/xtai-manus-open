"""空缓存实现：在未启用 Redis 时作为无副作用的占位实现。"""

from __future__ import annotations


class NullCache:
    """``CachePort`` 的空实现，所有读写均为 no-op。"""

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def ping(self) -> bool:
        return False

    def close(self) -> None:
        return None
