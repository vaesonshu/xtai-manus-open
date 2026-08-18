"""数据库连接与会话管理。"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.config import Settings
from infrastructure.persistence.models import Base

logger = logging.getLogger(__name__)


class Database:
    """SQLAlchemy 引擎与会话工厂封装。"""

    def __init__(self, settings: Settings) -> None:
        self._engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    @contextmanager
    def session(self) -> Iterator[Session]:
        """提供带提交/回滚的事务会话。"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """创建全部 ORM 表（主要用于测试环境）。"""
        Base.metadata.create_all(self._engine)

    def ping(self) -> bool:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:  # noqa: BLE001
            logger.exception("关闭数据库连接池失败")
