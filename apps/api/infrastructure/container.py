"""依赖注入容器：装配领域端口与基础设施实现。

DDD 中，基础设施层通过容器把具体实现注入应用层所需的端口，
表现层从这里获取装配好的应用服务。
"""

from __future__ import annotations

import logging

from application.agent.service import AgentApplicationService
from application.llm.invoke_service import LlmInvokeApplicationService
from application.llm.service import LlmConfigApplicationService
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.task.agent_task_runner import AgentTaskRunner
from application.agent.config import AgentExecutionConfig
from application.agent.react_executor import ReActExecutor
from application.agent.step_executor import StepExecutor
from application.task.execution_service import TaskExecutionApplicationService
from application.task.service import TaskApplicationService
from domain.ports import (
    AgentRunRepository,
    CachePort,
    EventBus,
    LlmConfigRepository,
    LlmRuntimePort,
)
from domain.task.ports import TaskRunnerPort
from langgraph.graph.state import CompiledStateGraph
from infrastructure.browser.http_browser import HttpBrowser
from infrastructure.browser.stub_browser import StubBrowser
from domain.ports.browser import BrowserPort
from infrastructure.json.repair_json_parser import RepairJsonParser
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.sandbox.local_sandbox import LocalSandbox
from infrastructure.search.baidu_search_engine import BaiduSearchEngine
from infrastructure.search.mock_search_engine import MockSearchEngine
from domain.ports.search_engine import SearchEnginePort
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
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from infrastructure.persistence.postgres_memory_repository import PostgresMemoryStoreRepository
from infrastructure.persistence.postgres_repository import PostgresAgentRunRepository
from infrastructure.persistence.repository import InMemoryAgentRunRepository
from infrastructure.tools import ToolRegistry, build_mock_toolkit
from infrastructure.tools.browser_toolkit import build_browser_toolkit
from infrastructure.tools.calculator_toolkit import build_calculator_toolkit
from infrastructure.tools.file_toolkit import build_file_toolkit
from infrastructure.tools.interaction_toolkit import build_interaction_toolkit
from infrastructure.tools.search_toolkit import build_search_toolkit
from infrastructure.tools.shell_toolkit import build_shell_toolkit
from infrastructure.tools.time_toolkit import build_time_toolkit
from infrastructure.task.task_execution_factory import TaskExecutionFactory
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.graph import build_agent_graph
from infrastructure.langgraph.task_runner import LangGraphTaskRunner
from infrastructure.persistence.checkpointer import get_checkpointer_for_settings

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

        # 记忆与多 Agent 规划
        self.memory_repository = self._build_memory_repository(settings)
        self.memory_service = MemoryApplicationService(self.memory_repository)
        self.planning_service = PlanningApplicationService(
            llm_runtime=self.llm_runtime,
            memory_service=self.memory_service,
        )
        self.task_repository = InMemoryTaskRepository()
        self.task_service = TaskApplicationService(self.task_repository)
        self.agent_graph: CompiledStateGraph | None = None

        sandbox = LocalSandbox(f"{settings.data_dir}/sandbox")
        search_engine = self._build_search_engine(settings)
        browser = self._build_browser(settings)
        json_parser = RepairJsonParser()
        tool_registry = ToolRegistry(
            [
                build_mock_toolkit(),
                build_calculator_toolkit(),
                build_time_toolkit(),
                build_interaction_toolkit(),
                build_shell_toolkit(sandbox),
                build_file_toolkit(sandbox),
                build_search_toolkit(search_engine),
                build_browser_toolkit(browser),
            ]
        )
        react_executor = ReActExecutor(
            llm_runtime=self.llm_runtime,
            memory_service=self.memory_service,
            tool_registry=tool_registry,
            json_parser=json_parser,
            config=AgentExecutionConfig(),
        )
        step_executor = StepExecutor(react_executor)
        self.agent_task_runner: TaskRunnerPort = self._build_task_runner(
            settings=settings,
            memory_service=self.memory_service,
            planning_service=self.planning_service,
            task_repository=self.task_repository,
            step_executor=step_executor,
        )
        use_redis = settings.redis_enabled and (
            settings.agent_orchestrator != "langgraph"
            or settings.langgraph_redis_execution
        )
        self.task_execution_factory = TaskExecutionFactory(
            use_redis=use_redis,
        )
        self.task_execution_service = TaskExecutionApplicationService(
            task_runner=self.agent_task_runner,
            task_service=self.task_service,
            execution_factory=self.task_execution_factory,
        )

    def _build_task_runner(
        self,
        *,
        settings: Settings,
        memory_service: MemoryApplicationService,
        planning_service: PlanningApplicationService,
        task_repository: InMemoryTaskRepository,
        step_executor: StepExecutor,
    ) -> TaskRunnerPort:
        """按配置选择应用层循环或 LangGraph 编排。"""
        self.agent_graph = None
        if settings.agent_orchestrator == "langgraph":
            emitter = GraphEventEmitter()
            node_deps = GraphNodeDependencies(
                planning_service=planning_service,
                memory_service=memory_service,
                step_executor=step_executor,
                task_repository=task_repository,
                settings=settings,
            )
            checkpointer = get_checkpointer_for_settings(settings)
            graph = build_agent_graph(
                settings,
                node_deps=node_deps,
                emitter=emitter,
                checkpointer=checkpointer,
            )
            self.agent_graph = graph
            return LangGraphTaskRunner(
                graph=graph,
                memory_service=memory_service,
                task_repository=task_repository,
                event_emitter=emitter,
                checkpointer=checkpointer,
                settings=settings,
            )

        return AgentTaskRunner(
            memory_service=memory_service,
            planning_service=planning_service,
            task_repository=task_repository,
            step_executor=step_executor,
            use_llm_planning=settings.agent_use_llm_planning,
            replan_after_each_step=settings.agent_replan_after_each_step,
        )

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

    def _build_memory_repository(self, settings: Settings) -> InMemoryMemoryStoreRepository | PostgresMemoryStoreRepository:
        if not settings.database_enabled:
            return InMemoryMemoryStoreRepository()
        if self.database is None:
            raise RuntimeError("database_enabled=True 但 Database 未初始化")
        return PostgresMemoryStoreRepository(self.database)

    @staticmethod
    def _build_browser(settings: Settings) -> BrowserPort:
        """按配置装配浏览器（默认 HTTP 抓取实现）。"""
        if settings.browser_backend == "stub":
            return StubBrowser()
        return HttpBrowser(
            timeout_seconds=settings.browser_timeout_seconds,
            max_content_chars=settings.browser_max_content_chars,
        )

    @staticmethod
    def _build_search_engine(settings: Settings) -> SearchEnginePort:
        """按配置装配搜索引擎（默认百度自研实现）。"""
        if settings.search_engine == "mock":
            return MockSearchEngine()
        return BaiduSearchEngine(
            max_results=settings.search_max_results,
            timeout_seconds=settings.search_timeout_seconds,
        )


def build_container(settings: Settings) -> Container:
    """构建应用容器。"""
    return Container(settings)
