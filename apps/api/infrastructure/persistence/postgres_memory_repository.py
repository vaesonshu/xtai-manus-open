"""PostgreSQL 任务记忆仓储实现。"""

from __future__ import annotations

from domain.memory.store import TaskMemoryStore
from domain.task.identifiers import TaskId
from infrastructure.persistence.database import Database
from infrastructure.persistence.memory_mapper import memory_store_from_dict, memory_store_to_dict
from infrastructure.persistence.models import TaskMemoryModel


class PostgresMemoryStoreRepository:
    """基于 PostgreSQL 的 ``MemoryStoreRepository`` 实现。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, store: TaskMemoryStore) -> None:
        payload = memory_store_to_dict(store)
        with self._database.session() as session:
            model = session.get(TaskMemoryModel, str(store.task_id))
            if model is None:
                model = TaskMemoryModel(
                    task_id=str(store.task_id),
                    data=payload,
                )
                session.add(model)
            else:
                model.data = payload

    def get(self, task_id: TaskId) -> TaskMemoryStore | None:
        with self._database.session() as session:
            model = session.get(TaskMemoryModel, str(task_id))
            if model is None:
                return None
            return memory_store_from_dict(model.data)

    def get_or_create(self, task_id: TaskId) -> TaskMemoryStore:
        existing = self.get(task_id)
        if existing is not None:
            return existing
        store = TaskMemoryStore.create(task_id)
        self.save(store)
        return store
