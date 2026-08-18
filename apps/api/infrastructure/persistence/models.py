"""SQLAlchemy ORM 模型（基础设施层，不泄漏到领域层）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """ORM 基类。"""


class AgentRunModel(Base):
    """agent 运行表：持久化 ``AgentRun`` 聚合根的快照。"""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # JSONB 在 PostgreSQL 上更高效；测试用 SQLite 时回退为通用 JSON
    result: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
