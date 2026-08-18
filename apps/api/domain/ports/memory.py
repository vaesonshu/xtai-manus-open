"""记忆存储仓储端口。"""

from __future__ import annotations

from typing import Protocol

from domain.memory.store import TaskMemoryStore
from domain.task.identifiers import TaskId


class MemoryStoreRepository(Protocol):
    """任务记忆聚合根持久化端口。"""

    def save(self, store: TaskMemoryStore) -> None:
        """保存记忆存储。"""
        ...

    def get(self, task_id: TaskId) -> TaskMemoryStore | None:
        """按任务 ID 读取。"""
        ...

    def get_or_create(self, task_id: TaskId) -> TaskMemoryStore:
        """读取或初始化任务记忆存储。"""
        ...
