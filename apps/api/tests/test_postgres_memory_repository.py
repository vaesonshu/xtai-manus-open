"""Postgres 任务记忆仓储测试。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.memory.kind import MemoryKind
from domain.task.identifiers import TaskId
from infrastructure.config import Settings
from infrastructure.persistence.database import Database
from infrastructure.persistence.postgres_memory_repository import PostgresMemoryStoreRepository


def test_postgres_memory_store_repository_roundtrip() -> None:
    settings = Settings(
        database_enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
    )
    database = Database(settings)
    database.create_tables()
    repository = PostgresMemoryStoreRepository(database)

    task_id = TaskId()
    store = repository.get_or_create(task_id)
    store.add_agent_message(
        AgentRole.RESEARCHER,
        {"role": "user", "content": "调研竞品"},
    )
    store.record(
        kind=MemoryKind.EPISODIC,
        content="用户目标：调研竞品",
        agent_role=AgentRole.COORDINATOR,
    )
    repository.save(store)

    loaded = repository.get(task_id)
    assert loaded is not None
    messages = loaded.get_agent_conversation(AgentRole.RESEARCHER).get_messages()
    assert messages[0]["content"] == "调研竞品"
    assert len(loaded.entries) == 1

    other = repository.get_or_create(TaskId())
    assert other.task_id.value != task_id.value
