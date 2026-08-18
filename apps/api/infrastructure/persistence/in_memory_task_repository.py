"""AgentTask 内存仓储。"""

from __future__ import annotations

from domain.task.identifiers import TaskId
from domain.task.task import AgentTask


class InMemoryTaskRepository:
    """进程内 AgentTask 仓储，适用于开发与测试。"""

    def __init__(self) -> None:
        self._store: dict[str, AgentTask] = {}

    def save(self, task: AgentTask) -> None:
        self._store[str(task.task_id)] = task

    def get(self, task_id: TaskId) -> AgentTask | None:
        return self._store.get(str(task_id))
