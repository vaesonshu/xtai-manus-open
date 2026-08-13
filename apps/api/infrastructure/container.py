"""依赖注入容器：装配领域端口与基础设施实现。

DDD 中，基础设施层通过容器把具体实现注入应用层所需的端口，
表现层从这里获取装配好的应用服务。
"""

from __future__ import annotations

from application.agent.service import AgentApplicationService
from domain.ports import AgentRunRepository, EventBus
from infrastructure.config import Settings
from infrastructure.events import InMemoryEventBus
from infrastructure.persistence.repository import InMemoryAgentRunRepository


class Container:
    """应用容器，持有全部已装配的依赖。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # 端口实现
        self.repository: AgentRunRepository = InMemoryAgentRunRepository()
        self.event_bus: EventBus = InMemoryEventBus()

        # 应用服务
        self.agent_service = AgentApplicationService(
            repository=self.repository,
            event_bus=self.event_bus,
        )


def build_container(settings: Settings) -> Container:
    """构建应用容器。"""
    return Container(settings)
