"""Checkpointer 工厂测试。"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from infrastructure.config import Settings
from infrastructure.persistence.checkpointer import (
    close_checkpointer,
    get_checkpointer,
    get_checkpointer_for_settings,
    get_checkpointer_info,
    init_checkpointer_for_settings,
    reset_checkpointer_state,
    resolve_checkpoint_backend,
    sqlalchemy_url_to_postgres_uri,
    _setup_postgres_checkpointer_migrations,
)


def test_sqlalchemy_url_to_postgres_uri() -> None:
    url = "postgresql+psycopg://postgres:postgres@localhost:5432/xtai"
    assert sqlalchemy_url_to_postgres_uri(url) == (
        "postgresql://postgres:postgres@localhost:5432/xtai"
    )


def test_resolve_checkpoint_backend_auto_without_db() -> None:
    settings = Settings(database_enabled=False, checkpoint_backend="auto")
    assert resolve_checkpoint_backend(settings) == "sqlite"


def test_resolve_checkpoint_backend_auto_with_db() -> None:
    settings = Settings(database_enabled=True, checkpoint_backend="auto")
    assert resolve_checkpoint_backend(settings) == "postgres"


def test_get_checkpointer_memory() -> None:
    saver = get_checkpointer(":memory:")
    assert isinstance(saver, InMemorySaver)


@pytest.mark.asyncio
async def test_init_checkpointer_for_settings_sqlite(tmp_path) -> None:
    reset_checkpointer_state()
    db_path = str(tmp_path / "cp.db")
    settings = Settings(
        checkpoint_backend="sqlite",
        checkpoint_db_path=db_path,
        database_enabled=False,
    )
    saver = await init_checkpointer_for_settings(settings)
    assert isinstance(saver, AsyncSqliteSaver)
    assert get_checkpointer_for_settings(settings) is saver
    await close_checkpointer(settings)


def test_checkpointer_info_memory() -> None:
    info = get_checkpointer_info(
        Settings(checkpoint_db_path=":memory:", checkpoint_backend="memory")
    )
    assert info.backend == "memory"


@pytest.mark.asyncio
async def test_setup_postgres_migrations_uses_autocommit_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Postgres 迁移应通过 from_conn_string（autocommit）执行，而非连接池事务。"""
    setup_calls: list[str] = []

    class FakeSetupSaver:
        async def setup(self) -> None:
            setup_calls.append("setup")

    class FakeContext:
        async def __aenter__(self) -> FakeSetupSaver:
            return FakeSetupSaver()

        async def __aexit__(self, *_args: object) -> None:
            return None

    def fake_from_conn_string(conn_uri: str):
        assert conn_uri == "postgresql://postgres:postgres@localhost:5433/xtai"
        return FakeContext()

    monkeypatch.setattr(
        "infrastructure.persistence.checkpointer.AsyncPostgresSaver.from_conn_string",
        fake_from_conn_string,
    )

    await _setup_postgres_checkpointer_migrations(
        "postgresql://postgres:postgres@localhost:5433/xtai"
    )
    assert setup_calls == ["setup"]
