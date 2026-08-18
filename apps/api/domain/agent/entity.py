"""agent 运行聚合根及其状态值对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from domain.agent.events import (
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunProgressed,
    AgentRunStarted,
)
from domain.exceptions import ConflictError, ValidationError
from domain.primitives import DomainEvent, RunId


class RunStatus(str, Enum):
    """运行状态（值对象）。"""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentRun:
    """agent 运行聚合根。

    封装一次自主任务的完整生命周期与领域事件。聚合根是唯一入口，
    外部只能通过其方法改变状态，保证业务不变量。
    """

    run_id: RunId
    goal: str
    status: RunStatus = RunStatus.CREATED
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(cls, goal: str, run_id: RunId | None = None) -> AgentRun:
        """创建一次新运行并发布 ``AgentRunStarted`` 事件。"""
        if not goal or not goal.strip():
            raise ValidationError("goal must not be empty")
        run = cls(run_id=run_id or RunId(), goal=goal.strip())
        run._events.append(AgentRunStarted(run_id=run.run_id, goal=run.goal))
        return run

    def start(self) -> None:
        """标记运行进入执行态。"""
        if self.status is not RunStatus.CREATED:
            raise ConflictError(f"cannot start run in status {self.status}")
        self.status = RunStatus.RUNNING

    def record_progress(self, step: int, message: str) -> None:
        """记录阶段性进展。"""
        if self.status is not RunStatus.RUNNING:
            raise ConflictError(f"cannot record progress in status {self.status}")
        self._events.append(
            AgentRunProgressed(run_id=self.run_id, step=step, message=message)
        )

    def complete(self, result: dict[str, Any]) -> None:
        """标记运行成功完成。"""
        if self.status is not RunStatus.RUNNING:
            raise ConflictError(f"cannot complete run in status {self.status}")
        self.status = RunStatus.COMPLETED
        self.result = result
        self._events.append(AgentRunCompleted(run_id=self.run_id, result=result))

    def fail(self, error: str) -> None:
        """标记运行失败。"""
        if self.status not in (RunStatus.CREATED, RunStatus.RUNNING):
            raise ConflictError(f"cannot fail run in status {self.status}")
        self.status = RunStatus.FAILED
        self.error = error
        self._events.append(AgentRunFailed(run_id=self.run_id, error=error))

    def pull_events(self) -> list[DomainEvent]:
        """取出并清空累积的领域事件。"""
        events = self._events
        self._events = []
        return events
