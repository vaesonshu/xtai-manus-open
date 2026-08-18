"""依赖注入容器：装配领域端口与基础设施实现。

DDD 中，基础设施层通过容器把具体实现注入应用层所需的端口，
表现层从这里获取装配好的应用服务。
"""

from __future__ import annotations

import logging

from application.agent.service import AgentApplicationService
from application.llm.invoke_service import LlmInvokeApplicationService
from application.llm.service import LlmConfigApplicationService
from domain.ports import (
    AgentRunRepository,
    CachePort,
    EventBus,
    LlmConfigRepository,
    LlmRuntimePort,
)
from infrastructure.cache import NullCache, RedisCache
from infrastructure.config import Settings
from infrastructure.events import InMemoryEventBus
from infrastructure.llm.chat import bind_runtime
from infrastructure.llm.config_repository import InMemoryLlmConfigRepository
from infrastructure.llm.factory import llm_config_from_settings
from infrastructure.llm.runtime import LlmRuntime
from infrastructure.persistence.caching_repository import CachingAgentRunRepository
from infrastructure.persistence.database import Database
from infrastructure.persistence.llm_config_repository import PostgresLlmConfigRepository
from infrastructure.persistence.postgres_repository import PostgresAgentRunRepository
from infrastructure.persistence.repository import InMemoryAgentRunRepository

logger = logging.getLogger(__name__)


class Container:
    """应用容器，持有全部已装配的依赖。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # 外部基础设施
        self.cache: CachePort = self._build_cache(settings)
        self.database: Database | None = self._build_database(settings)

        # LLM 运行时（支持热更新与后台线程池）
        default_llm_config = llm_config_from_settings(settings)
        self.llm_runtime: LlmRuntimePort = LlmRuntime(default_llm_config)
        bind_runtime(self.llm_runtime)  # type: ignore[arg-type]

        # 端口实现
        base_repository: AgentRunRepository = self._build_base_repository(settings)
        self.repository: AgentRunRepository = self._build_repository(
            base_repository,
            settings,
        )
        self.llm_config_repository: LlmConfigRepository = self._build_llm_config_repository(
            settings,
        )
        self.event_bus: EventBus = InMemoryEventBus()

        # 应用服务
        self.agent_service = AgentApplicationService(
            repository=self.repository,
            event_bus=self.event_bus,
        )
        self.llm_config_service = LlmConfigApplicationService(
            repository=self.llm_config_repository,
            runtime=self.llm_runtime,
            event_bus=self.event_bus,
            default_config_factory=lambda: llm_config_from_settings(settings),
        )
        self.llm_invoke_service = LlmInvokeApplicationService(runtime=self.llm_runtime)

    def cache_health(self) -> str:
        """返回 Redis 健康状态：ok / disabled / error。"""
        if not self.settings.redis_enabled:
            return "disabled"
        try:
            return "ok" if self.cache.ping() else "error"
        except Exception:  # noqa: BLE001
            logger.exception("Redis 健康检查失败")
            return "error"

    def database_health(self) -> str:
        """返回 PostgreSQL 健康状态：ok / disabled / error。"""
        if not self.settings.database_enabled:
            return "disabled"
        if self.database is None:
            return "error"
        try:
            return "ok" if self.database.ping() else "error"
        except Exception:  # noqa: BLE001
            logger.exception("PostgreSQL 健康检查失败")
            return "error"

    def close(self) -> None:
        """释放容器持有的外部资源。"""
        self.cache.close()
        if self.database is not None:
            self.database.close()
        if isinstance(self.llm_runtime, LlmRuntime):
            self.llm_runtime.shutdown()

    def _build_cache(self, settings: Settings) -> CachePort:
        if not settings.redis_enabled:
            return NullCache()
        return RedisCache(settings)

    def _build_database(self, settings: Settings) -> Database | None:
        if not settings.database_enabled:
            return None
        return Database(settings)

    def _build_base_repository(self, settings: Settings) -> AgentRunRepository:
        if not settings.database_enabled:
            return InMemoryAgentRunRepository()
        if self.database is None:
            raise RuntimeError("database_enabled=True 但 Database 未初始化")
        return PostgresAgentRunRepository(self.database)

    def _build_repository(
        self,
        base_repository: AgentRunRepository,
        settings: Settings,
    ) -> AgentRunRepository:
        if not settings.redis_enabled:
            return base_repository
        return CachingAgentRunRepository(
            repository=base_repository,
            cache=self.cache,
            ttl_seconds=settings.redis_default_ttl,
        )

    def _build_llm_config_repository(self, settings: Settings) -> LlmConfigRepository:
        if not settings.database_enabled:
            return InMemoryLlmConfigRepository()
        if self.database is None:
            raise RuntimeError("database_enabled=True 但 Database 未初始化")
        return PostgresLlmConfigRepository(self.database)


def build_container(settings: Settings) -> Container:
    """构建应用容器。"""
    return Container(settings)
