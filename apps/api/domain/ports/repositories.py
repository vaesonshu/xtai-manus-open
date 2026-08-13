"""领域端口（Ports）：定义领域层所需的外部能力，由基础设施层实现。

端口使用 ``typing.Protocol`` 定义，领域层不依赖具体实现，实现运行时注入。
"""

from __future__ import annotations

from typing import Protocol

from domain.agent.entity import AgentRun
from domain.primitives import DomainEvent, RunId


class AgentRunRepository(Protocol):
    """agent 运行仓库端口。"""

    def save(self, run: AgentRun) -> None:
        """持久化一次运行（新增或更新）。"""
        ...

    def get(self, run_id: RunId) -> AgentRun | None:
        """按 ID 读取运行；不存在返回 ``None``。"""
        ...


class EventBus(Protocol):
    """领域事件总线端口。"""

    def publish(self, event: DomainEvent) -> None:
        """发布一个领域事件。"""
        ...
