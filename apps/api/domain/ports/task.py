"""Task 子域仓储端口。"""

from __future__ import annotations

from typing import Protocol

from domain.task.identifiers import TaskId
from domain.task.task import AgentTask


class TaskRepository(Protocol):
    """任务聚合根持久化端口。"""

    def save(self, task: AgentTask) -> None:
        """保存任务（新增或更新）。"""
        ...

    def get(self, task_id: TaskId) -> AgentTask | None:
        """按 ID 读取任务。"""
        ...
