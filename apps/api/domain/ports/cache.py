"""缓存端口：定义键值缓存能力，由基础设施层用 Redis 等实现。"""

from __future__ import annotations

from typing import Protocol


class CachePort(Protocol):
    """通用缓存端口（字符串键值）。"""

    def get(self, key: str) -> str | None:
        """读取缓存；未命中返回 ``None``。"""
        ...

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """写入缓存，可选 TTL（秒）。"""
        ...

    def delete(self, key: str) -> None:
        """删除指定键。"""
        ...

    def ping(self) -> bool:
        """探测缓存后端是否可用。"""
        ...

    def close(self) -> None:
        """释放连接等资源。"""
        ...
