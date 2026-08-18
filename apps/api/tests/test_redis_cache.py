"""缓存仓库与 Redis 适配器测试。"""

from __future__ import annotations

import fakeredis

from domain.agent.entity import AgentRun
from infrastructure.cache.redis_cache import RedisCache
from infrastructure.config import Settings
from infrastructure.persistence.caching_repository import CachingAgentRunRepository
from infrastructure.persistence.repository import InMemoryAgentRunRepository


class InMemoryCache:
    """测试用内存缓存，实现 ``CachePort`` 协议。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        return None


def test_caching_repository_reads_from_cache_after_save() -> None:
    """保存后再次读取应命中缓存（底层仓库清空后仍可读到）。"""
    base_repo = InMemoryAgentRunRepository()
    cache = InMemoryCache()
    repo = CachingAgentRunRepository(base_repo, cache, ttl_seconds=60)

    run = AgentRun.create(goal="测试缓存")
    repo.save(run)

    # 模拟底层仓库数据丢失，若仍能从缓存读到则说明缓存生效
    base_repo._store.clear()
    cached_run = repo.get(run.run_id)

    assert cached_run is not None
    assert cached_run.goal == "测试缓存"


def test_redis_cache_with_fakeredis() -> None:
    """Redis 适配器应能通过 fakeredis 正常读写。"""
    settings = Settings(
        redis_enabled=True,
        redis_url="redis://localhost:6379/0",
        redis_key_prefix="test",
    )
    cache = RedisCache(settings)
    # 注入 fakeredis 客户端，避免依赖真实 Redis 服务
    cache._client = fakeredis.FakeRedis(decode_responses=True)  # type: ignore[attr-defined]

    cache.set("demo", "value", ttl_seconds=30)
    assert cache.get("demo") == "value"
    assert cache.ping() is True
    cache.close()


def test_cache_repository_falls_back_when_cache_fails() -> None:
    """缓存故障时应回落到底层仓库，不阻断业务。"""

    class BrokenCache:
        def get(self, key: str) -> str | None:
            raise ConnectionError("redis down")

        def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
            raise ConnectionError("redis down")

        def delete(self, key: str) -> None:
            raise ConnectionError("redis down")

        def ping(self) -> bool:
            return False

        def close(self) -> None:
            return None

    base_repo = InMemoryAgentRunRepository()
    repo = CachingAgentRunRepository(base_repo, BrokenCache(), ttl_seconds=60)

    run = AgentRun.create(goal="回落测试")
    repo.save(run)

    loaded = repo.get(run.run_id)
    assert loaded is not None
    assert loaded.goal == "回落测试"
