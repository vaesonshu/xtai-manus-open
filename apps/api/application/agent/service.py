"""应用层服务：用例编排。

应用服务只依赖领域层的端口（Protocol），由基础设施层在运行时注入具体实现。
"""

from __future__ import annotations

from application.agent.dto import AgentRunDTO, StartAgentRunCommand
from domain.agent.entity import AgentRun
from domain.ports import AgentRunRepository, EventBus
from domain.primitives import RunId


class AgentApplicationService:
    """agent 用例编排服务。"""

    def __init__(self, repository: AgentRunRepository, event_bus: EventBus) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def start(self, command: StartAgentRunCommand) -> AgentRunDTO:
        """发起一次运行：创建聚合根、持久化并发布领域事件。

        注意：真实执行由 LangGraph 异步编排器负责；这里只负责创建与登记，
        避免在同步请求中阻塞于 LLM 调用。
        """
        run = AgentRun.create(goal=command.goal)
        run.start()

        self._repository.save(run)
        for event in run.pull_events():
            self._event_bus.publish(event)

        return AgentRunDTO.from_entity(
            run_id=run.run_id,
            goal=run.goal,
            status=run.status,
            result=run.result,
            error=run.error,
        )

    def get(self, run_id: str) -> AgentRunDTO | None:
        """按 ID 查询运行状态。"""
        run = self._repository.get(RunId(run_id))
        if run is None:
            return None
        return AgentRunDTO.from_entity(
            run_id=run.run_id,
            goal=run.goal,
            status=run.status,
            result=run.result,
            error=run.error,
        )
