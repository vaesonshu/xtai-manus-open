"""PostgreSQL 仓库测试（使用 SQLite 内存库验证 SQLAlchemy 逻辑）。"""

from __future__ import annotations

from domain.agent.entity import AgentRun
from infrastructure.config import Settings
from infrastructure.persistence.database import Database
from infrastructure.persistence.postgres_repository import PostgresAgentRunRepository


def test_postgres_repository_save_and_get() -> None:
    """保存后应能按 ID 读取聚合根。"""
    settings = Settings(
        database_enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
    )
    database = Database(settings)
    database.create_tables()
    repository = PostgresAgentRunRepository(database)

    run = AgentRun.create(goal="持久化测试")
    run.start()
    repository.save(run)

    loaded = repository.get(run.run_id)
    assert loaded is not None
    assert loaded.goal == "持久化测试"
    assert loaded.status.value == "running"


def test_postgres_repository_update_existing_run() -> None:
    """重复保存同一 run_id 应执行更新而非插入。"""
    settings = Settings(
        database_enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
    )
    database = Database(settings)
    database.create_tables()
    repository = PostgresAgentRunRepository(database)

    run = AgentRun.create(goal="初始目标")
    run.start()
    repository.save(run)

    run.complete(result={"answer": 42})
    repository.save(run)

    loaded = repository.get(run.run_id)
    assert loaded is not None
    assert loaded.status.value == "completed"
    assert loaded.result == {"answer": 42}
