"""任务规划实体：将用户目标拆解为可执行步骤。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.agent.role import AgentRole
from domain.exceptions import ConflictError, ValidationError
from domain.task.identifiers import PlanId
from domain.task.status import ExecutionStatus
from domain.task.step import TaskStep

if TYPE_CHECKING:
    from domain.planning.step_spec import PlanStepSpec


@dataclass
class TaskPlan:
    """任务规划实体。

    关注点：步骤编排与「下一步」选择，不处理后台调度或消息流。
    """

    plan_id: PlanId
    title: str
    goal: str
    language: str = "zh-CN"
    message: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    steps: list[TaskStep] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        goal: str,
        language: str = "zh-CN",
        message: str = "",
        steps: list[TaskStep] | None = None,
        plan_id: PlanId | None = None,
    ) -> TaskPlan:
        """创建规划并校验基本不变量。"""
        if not title.strip():
            raise ValidationError("plan title must not be empty")
        if not goal.strip():
            raise ValidationError("plan goal must not be empty")
        return cls(
            plan_id=plan_id or PlanId(),
            title=title.strip(),
            goal=goal.strip(),
            language=language.strip() or "zh-CN",
            message=message,
            steps=list(steps or []),
        )

    @property
    def done(self) -> bool:
        """规划是否已结束。"""
        return self.status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}

    def add_step(
        self,
        description: str,
        *,
        agent_role: AgentRole = AgentRole.EXECUTOR,
    ) -> TaskStep:
        """向规划追加步骤（仅允许在未完成状态下操作）。"""
        if self.done:
            raise ConflictError("cannot add step to a finished plan")
        step = TaskStep.create(description, agent_role=agent_role)
        self.steps.append(step)
        return step

    def add_steps_from_specs(self, specs: list[PlanStepSpec]) -> list[TaskStep]:
        """批量追加多 Agent 步骤。"""
        return [self.add_step(spec.description, agent_role=spec.agent_role) for spec in specs]

    def revise(self, new_specs: list[PlanStepSpec], reason: str = "") -> list[TaskStep]:
        """动态重规划：跳过未完成的旧步骤并追加新步骤。"""
        if self.done:
            raise ConflictError(f"cannot revise plan in status {self.status}")

        skip_reason = reason or "plan revised"
        for step in self.steps:
            if not step.done:
                step.skip(skip_reason)

        return self.add_steps_from_specs(new_specs)

    def get_next_step(self) -> TaskStep | None:
        """获取下一个待执行步骤。"""
        return next((step for step in self.steps if not step.done), None)

    def start(self) -> None:
        """标记规划进入执行。"""
        if self.status is not ExecutionStatus.PENDING:
            raise ConflictError(f"cannot start plan in status {self.status}")
        if not self.steps:
            raise ValidationError("plan must contain at least one step")
        self.status = ExecutionStatus.RUNNING

    def complete(self) -> None:
        """标记规划完成（通常在所有步骤结束后调用）。"""
        if self.status is not ExecutionStatus.RUNNING:
            raise ConflictError(f"cannot complete plan in status {self.status}")
        if any(not step.done for step in self.steps):
            raise ConflictError("cannot complete plan while steps are pending")
        self.status = ExecutionStatus.COMPLETED

    def fail(self, error: str) -> None:
        """标记规划失败。"""
        if self.done:
            raise ConflictError(f"cannot fail plan in status {self.status}")
        self.status = ExecutionStatus.FAILED
        self.error = error
