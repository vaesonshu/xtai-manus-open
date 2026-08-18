"""Checkpointer 工厂：支持 memory / sqlite / postgres（Phase 5 生产加固）。

LangGraph 的 ``ainvoke`` 需要异步 checkpointer（``aget_tuple`` 等）。
同步 ``SqliteSaver`` / ``PostgresSaver`` 会在异步路径抛出 ``NotImplementedError``。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from psycopg_pool import AsyncConnectionPool

from infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)

CheckpointBackend = Literal["auto", "memory", "sqlite", "postgres"]

# 应用生命周期内复用的单例与底层连接
_checkpointer: BaseCheckpointSaver | None = None
_sqlite_conn: aiosqlite.Connection | None = None
_postgres_pool: AsyncConnectionPool | None = None


@dataclass(frozen=True)
class CheckpointerInfo:
    """当前 checkpointer 元信息（健康检查 / 可观测性）。"""

    backend: str
    detail: str


def resolve_checkpoint_backend(settings: Settings) -> str:
    """解析实际使用的 checkpoint 后端。"""
    if settings.checkpoint_backend != "auto":
        return settings.checkpoint_backend
    if settings.database_enabled:
        return "postgres"
    return "sqlite"


def sqlalchemy_url_to_postgres_uri(database_url: str) -> str:
    """将 SQLAlchemy URL 转为 psycopg 连接串。"""
    url = database_url.strip()
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def get_checkpointer_info(settings: Settings | None = None) -> CheckpointerInfo:
    """返回当前 checkpointer 配置摘要。"""
    resolved = settings or get_settings()
    backend = resolve_checkpoint_backend(resolved)
    if backend == "memory" or resolved.checkpoint_db_path == ":memory:":
        return CheckpointerInfo(backend="memory", detail="in-process")
    if backend == "sqlite":
        return CheckpointerInfo(backend="sqlite", detail=resolved.checkpoint_db_path)
    return CheckpointerInfo(
        backend="postgres",
        detail=sqlalchemy_url_to_postgres_uri(resolved.database_url),
    )


async def _create_sqlite_checkpointer(checkpoint_db_path: str) -> AsyncSqliteSaver:
    """创建 AsyncSqliteSaver 并初始化表结构。"""
    global _sqlite_conn
    path = Path(checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _sqlite_conn = await aiosqlite.connect(str(path.resolve()))
    saver = AsyncSqliteSaver(_sqlite_conn)
    await saver.setup()
    logger.info("LangGraph AsyncSqliteSaver 已初始化: %s", path)
    return saver


async def _create_postgres_checkpointer(database_url: str) -> AsyncPostgresSaver:
    """创建 AsyncPostgresSaver 并初始化表结构。"""
    global _postgres_pool
    conn_uri = sqlalchemy_url_to_postgres_uri(database_url)
    _postgres_pool = AsyncConnectionPool(conn_uri, min_size=1, max_size=5, open=False)
    await _postgres_pool.open()
    saver = AsyncPostgresSaver(_postgres_pool)
    await saver.setup()
    logger.info("LangGraph AsyncPostgresSaver 已初始化")
    return saver


async def init_checkpointer_for_settings(settings: Settings) -> BaseCheckpointSaver:
    """在应用 lifespan 中异步初始化 checkpointer（生产入口）。"""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    if settings.checkpoint_db_path == ":memory:":
        _checkpointer = InMemorySaver()
        return _checkpointer

    backend = resolve_checkpoint_backend(settings)
    if backend == "memory":
        _checkpointer = InMemorySaver()
        return _checkpointer

    if backend == "postgres" and settings.database_enabled:
        try:
            _checkpointer = await _create_postgres_checkpointer(settings.database_url)
            return _checkpointer
        except Exception:  # noqa: BLE001
            logger.exception("Postgres checkpointer 初始化失败，回退 sqlite")

    _checkpointer = await _create_sqlite_checkpointer(settings.checkpoint_db_path)
    return _checkpointer


def get_checkpointer_for_settings(settings: Settings) -> BaseCheckpointSaver:
    """获取已初始化的 checkpointer。

    内存模式可在测试中同步创建；sqlite/postgres 必须先 ``await init_checkpointer_for_settings``。
    """
    if _checkpointer is not None:
        return _checkpointer

    if settings.checkpoint_db_path == ":memory:":
        return InMemorySaver()

    backend = resolve_checkpoint_backend(settings)
    if backend == "memory":
        return InMemorySaver()

    raise RuntimeError(
        "Checkpointer 尚未初始化：请在应用 lifespan 中调用 init_checkpointer_for_settings"
    )


@lru_cache
def get_checkpointer(checkpoint_db_path: str = "./data/checkpoints.db") -> BaseCheckpointSaver:
    """测试用简化入口（仅支持 :memory:）。"""
    if checkpoint_db_path == ":memory:":
        return InMemorySaver()
    raise RuntimeError(
        "测试若使用 sqlite 文件，请调用 await init_checkpointer_for_settings(settings)"
    )


async def close_checkpointer(settings: Settings | None = None) -> None:
    """释放 checkpointer 资源。"""
    global _checkpointer, _sqlite_conn, _postgres_pool
    resolved = settings or get_settings()

    if _postgres_pool is not None:
        try:
            await _postgres_pool.close()
        except Exception:  # noqa: BLE001
            logger.exception("关闭 Postgres checkpointer 连接池失败")
        _postgres_pool = None

    if _sqlite_conn is not None:
        try:
            await _sqlite_conn.close()
        except Exception:  # noqa: BLE001
            logger.exception("关闭 SQLite checkpointer 连接失败")
        _sqlite_conn = None

    _checkpointer = None
    get_checkpointer.cache_clear()


def reset_checkpointer_state() -> None:
    """测试用：仅重置模块内引用，不关闭底层连接。"""
    global _checkpointer, _sqlite_conn, _postgres_pool
    _checkpointer = None
    _sqlite_conn = None
    _postgres_pool = None
    get_checkpointer.cache_clear()
