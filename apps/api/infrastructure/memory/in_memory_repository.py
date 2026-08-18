"""内存记忆仓储实现。"""

from __future__ import annotations

from domain.memory.store import TaskMemoryStore
from domain.task.identifiers import TaskId


class InMemoryMemoryStoreRepository:
    """进程内记忆存储，适用于开发与测试。"""

    def __init__(self) -> None:
        self._stores: dict[str, TaskMemoryStore] = {}

    def save(self, store: TaskMemoryStore) -> None:
        self._stores[str(store.task_id)] = store

    def get(self, task_id: TaskId) -> TaskMemoryStore | None:
        return self._stores.get(str(task_id))

    def get_or_create(self, task_id: TaskId) -> TaskMemoryStore:
        existing = self.get(task_id)
        if existing is not None:
            return existing
        store = TaskMemoryStore.create(task_id)
        self.save(store)
        return store
