"""持久化适配器：内存仓库实现 + SQLite checkpointer 封装。

``InMemoryAgentRunRepository`` 是 ``AgentRunRepository`` 端口的简单实现，
便于开发与测试；生产可替换为数据库实现。
"""

from __future__ import annotations

from domain.agent.entity import AgentRun
from domain.primitives import RunId


class InMemoryAgentRunRepository:
    """基于字典的内存仓库。"""

    def __init__(self) -> None:
        self._store: dict[str, AgentRun] = {}

    def save(self, run: AgentRun) -> None:
        self._store[str(run.run_id)] = run

    def get(self, run_id: RunId) -> AgentRun | None:
        return self._store.get(str(run_id))
