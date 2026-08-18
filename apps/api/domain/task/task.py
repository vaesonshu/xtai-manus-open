"""任务聚合根：编排生命周期、规划与步骤执行入口。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent.role import AgentRole
from domain.exceptions import ConflictError, ValidationError
from domain.planning.step_spec import PlanStepSpec
from domain.task.events import (
    TaskCancelled,
    TaskCompleted,
    TaskCreated,
    TaskDomainEvent,
    TaskFailed,
    TaskPlanAttached,
    TaskPlanRevised,
    TaskStarted,
    TaskStepCompleted,
    TaskStepFailed,
    TaskStepStarted,
    TaskWaiting,
)
from domain.task.identifiers import TaskId
from domain.task.plan import TaskPlan
from domain.task.plan_snapshot import PlanSnapshot
from domain.task.status import ExecutionStatus, TaskStatus
from domain.task.step import TaskStep


@dataclass
class AgentTask:
    """Agent 任务聚合根。

    关注点分离：
    - **生命周期**：``start / wait / complete / fail / cancel``
    - **规划**：通过 ``TaskPlan`` 管理步骤，不内联步骤细节
    - **执行**：具体调度由 ``TaskRunnerPort`` 等基础设施端口负责
    """

    task_id: TaskId
    goal: str
    status: TaskStatus = TaskStatus.CREATED
    plan: TaskPlan | None = None
    plan_history: list[PlanSnapshot] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    # 等待用户输入时，记录是哪个 Agent 发起的提问
    waiting_agent_role: AgentRole | None = None

    _events: list[TaskDomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(cls, goal: str, task_id: TaskId | None = None) -> AgentTask:
        """创建新任务。"""
        if not goal or not goal.strip():
            raise ValidationError("task goal must not be empty")
        task = cls(task_id=task_id or TaskId(), goal=goal.strip())
        task._events.append(TaskCreated(task_id=task.task_id, goal=task.goal))
        return task

    def attach_plan(self, plan: TaskPlan) -> None:
        """关联规划（Planner 产出后挂载到任务）。"""
        if self.plan is not None:
            raise ConflictError("task already has an attached plan")
        if plan.goal.strip() != self.goal.strip():
            raise ValidationError("plan goal must match task goal")
        self.plan = plan
        self._record_plan_snapshot("initial")
        self._events.append(
            TaskPlanAttached(task_id=self.task_id, plan_id=plan.plan_id)
        )

    def get_latest_plan_snapshot(self) -> PlanSnapshot | None:
        """获取最新规划快照。"""
        return self.plan_history[-1] if self.plan_history else None

    def start(self) -> None:
        """启动任务执行。"""
        if self.status is not TaskStatus.CREATED:
            raise ConflictError(f"cannot start task in status {self.status}")
        self.status = TaskStatus.RUNNING
        self._events.append(TaskStarted(task_id=self.task_id))

    def wait_for_input(
        self,
        reason: str = "",
        *,
        agent_role: AgentRole | None = None,
    ) -> None:
        """进入等待用户输入状态（Manus 类交互场景）。"""
        if self.status is not TaskStatus.RUNNING:
            raise ConflictError(f"cannot wait in status {self.status}")
        self.status = TaskStatus.WAITING
        self.waiting_agent_role = agent_role
        self._events.append(TaskWaiting(task_id=self.task_id, reason=reason))

    def resume(self) -> None:
        """从等待状态恢复执行。"""
        if self.status is not TaskStatus.WAITING:
            raise ConflictError(f"cannot resume task in status {self.status}")
        self.status = TaskStatus.RUNNING
        self.waiting_agent_role = None

    def begin_next_step(self) -> TaskStep:
        """开始执行规划中的下一步，并发布步骤开始事件。"""
        if self.status is not TaskStatus.RUNNING:
            raise ConflictError(f"cannot begin step in status {self.status}")
        if self.plan is None:
            raise ConflictError("task has no attached plan")

        step = self.plan.get_next_step()
        if step is None:
            raise ConflictError("no pending step available")

        if self.plan.status is ExecutionStatus.PENDING:
            self.plan.start()

        step.start()
        self._events.append(
            TaskStepStarted(
                task_id=self.task_id,
                step_id=step.step_id,
                description=step.description,
                agent_role=step.agent_role,
            )
        )
        return step

    def replan(self, new_specs: list[PlanStepSpec], reason: str = "") -> list[TaskStep]:
        """动态重规划并发布事件。"""
        if self.plan is None:
            raise ConflictError("task has no attached plan")
        added = self.plan.revise(new_specs, reason=reason)
        self._record_plan_snapshot(reason or "revised")
        self._events.append(
            TaskPlanRevised(
                task_id=self.task_id,
                plan_id=self.plan.plan_id,
                reason=reason,
                added_step_count=len(added),
            )
        )
        return added

    def complete_current_step(self, result: str) -> TaskStep:
        """完成当前运行中的步骤。"""
        step = self._require_running_step()
        step.complete(result)
        self._events.append(
            TaskStepCompleted(
                task_id=self.task_id,
                step_id=step.step_id,
                result=result,
            )
        )
        if self.plan is not None and self.plan.get_next_step() is None:
            self.plan.complete()
        return step

    def fail_current_step(self, error: str) -> TaskStep:
        """标记当前步骤失败，并联动规划与任务失败。"""
        step = self._require_running_step()
        step.fail(error)
        self._events.append(
            TaskStepFailed(task_id=self.task_id, step_id=step.step_id, error=error)
        )
        if self.plan is not None:
            self.plan.fail(error)
        self.fail(error)
        return step

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """完成任务。"""
        if self.status not in (TaskStatus.RUNNING, TaskStatus.WAITING):
            raise ConflictError(f"cannot complete task in status {self.status}")
        self.status = TaskStatus.COMPLETED
        self.result = result or {}
        self._events.append(TaskCompleted(task_id=self.task_id, result=self.result))

    def fail(self, error: str) -> None:
        """标记任务失败。"""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise ConflictError(f"cannot fail task in status {self.status}")
        self.status = TaskStatus.FAILED
        self.error = error
        self._events.append(TaskFailed(task_id=self.task_id, error=error))

    def cancel(self, reason: str = "") -> None:
        """取消任务。"""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise ConflictError(f"cannot cancel task in status {self.status}")
        self.status = TaskStatus.CANCELLED
        self.error = reason or self.error
        self._events.append(TaskCancelled(task_id=self.task_id, reason=reason))

    def pull_events(self) -> list[TaskDomainEvent]:
        """取出并清空领域事件。"""
        events = self._events
        self._events = []
        return events

    def _record_plan_snapshot(self, reason: str) -> None:
        """将当前规划写入版本链。"""
        if self.plan is None:
            return
        snapshot = PlanSnapshot.from_plan(
            self.plan,
            version=len(self.plan_history) + 1,
            reason=reason,
        )
        self.plan_history.append(snapshot)

    def _require_running_step(self) -> TaskStep:
        if self.plan is None:
            raise ConflictError("task has no attached plan")
        step = next(
            (item for item in self.plan.steps if item.status is ExecutionStatus.RUNNING),
            None,
        )
        if step is None:
            raise ConflictError("no running step to complete or fail")
        return step
