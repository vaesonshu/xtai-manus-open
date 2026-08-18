"""PostgreSQL 仓库实现：通过 SQLAlchemy 持久化 ``AgentRun`` 聚合根。"""

from __future__ import annotations

from domain.agent.entity import AgentRun, RunStatus
from domain.primitives import RunId
from infrastructure.persistence.database import Database
from infrastructure.persistence.models import AgentRunModel


def _to_entity(model: AgentRunModel) -> AgentRun:
    """ORM 行 → 领域聚合根。"""
    return AgentRun(
        run_id=RunId(model.id),
        goal=model.goal,
        status=RunStatus(model.status),
        result=model.result or {},
        error=model.error,
    )


def _apply_entity(model: AgentRunModel, run: AgentRun) -> None:
    """将聚合根状态写入 ORM 模型。"""
    model.goal = run.goal
    model.status = run.status.value
    model.result = run.result
    model.error = run.error


class PostgresAgentRunRepository:
    """基于 PostgreSQL 的 ``AgentRunRepository`` 实现。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, run: AgentRun) -> None:
        with self._database.session() as session:
            model = session.get(AgentRunModel, str(run.run_id))
            if model is None:
                model = AgentRunModel(
                    id=str(run.run_id),
                    goal=run.goal,
                    status=run.status.value,
                    result=run.result,
                    error=run.error,
                )
                session.add(model)
            else:
                _apply_entity(model, run)

    def get(self, run_id: RunId) -> AgentRun | None:
        with self._database.session() as session:
            model = session.get(AgentRunModel, str(run_id))
            if model is None:
                return None
            return _to_entity(model)
