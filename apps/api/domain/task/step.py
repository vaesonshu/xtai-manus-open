"""任务步骤实体：规划子域中的最小执行单元。"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.agent.role import AgentRole
from domain.exceptions import ConflictError, ValidationError
from domain.task.identifiers import StepId
from domain.task.status import ExecutionStatus


@dataclass
class TaskStep:
    """规划步骤实体。

    关注点：描述「谁做什么」以及步骤级执行结果，不承载任务级生命周期逻辑。
    """

    step_id: StepId
    description: str
    agent_role: AgentRole = AgentRole.EXECUTOR
    status: ExecutionStatus = ExecutionStatus.PENDING
    success: bool | None = None
    result: str | None = None
    error: str | None = None
    attachments: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        description: str,
        *,
        agent_role: AgentRole = AgentRole.EXECUTOR,
        step_id: StepId | None = None,
    ) -> TaskStep:
        """创建待执行步骤。"""
        if not description or not description.strip():
            raise ValidationError("step description must not be empty")
        return cls(
            step_id=step_id or StepId(),
            description=description.strip(),
            agent_role=agent_role,
        )

    @property
    def done(self) -> bool:
        """步骤是否已结束（成功、失败或跳过）。"""
        return self.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
        }

    def start(self) -> None:
        """标记步骤进入执行态。"""
        if self.status is not ExecutionStatus.PENDING:
            raise ConflictError(f"cannot start step in status {self.status}")
        self.status = ExecutionStatus.RUNNING

    def complete(
        self,
        result: str,
        *,
        success: bool = True,
        attachments: tuple[str, ...] = (),
    ) -> None:
        """标记步骤成功完成。"""
        if self.status is not ExecutionStatus.RUNNING:
            raise ConflictError(f"cannot complete step in status {self.status}")
        self.status = ExecutionStatus.COMPLETED
        self.success = success
        self.result = result
        self.attachments = attachments

    def fail(self, error: str) -> None:
        """标记步骤失败。"""
        if self.status not in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
            raise ConflictError(f"cannot fail step in status {self.status}")
        self.status = ExecutionStatus.FAILED
        self.error = error

    def skip(self, reason: str = "") -> None:
        """跳过步骤（如 Planner 动态调整计划时）。"""
        if self.done:
            raise ConflictError(f"cannot skip step in status {self.status}")
        self.status = ExecutionStatus.SKIPPED
        self.result = reason or None
