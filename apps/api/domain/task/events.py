"""Task 子域领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent.role import AgentRole
from domain.primitives import Timestamp
from domain.task.identifiers import PlanId, StepId, TaskId


@dataclass
class TaskDomainEvent:
    """Task 子域事件基类。"""

    task_id: TaskId
    occurred_at: Timestamp = field(default_factory=Timestamp)

    @property
    def name(self) -> str:
        return type(self).__name__

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "task_id": str(self.task_id),
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class TaskCreated(TaskDomainEvent):
    """任务已创建。"""

    goal: str = ""


@dataclass
class TaskStarted(TaskDomainEvent):
    """任务进入执行。"""


@dataclass
class TaskWaiting(TaskDomainEvent):
    """任务等待用户输入或外部事件。"""

    reason: str = ""


@dataclass
class TaskPlanAttached(TaskDomainEvent):
    """任务已关联规划。"""

    plan_id: PlanId = field(default_factory=PlanId)


@dataclass
class TaskPlanRevised(TaskDomainEvent):
    """任务规划已动态调整。"""

    plan_id: PlanId = field(default_factory=PlanId)
    reason: str = ""
    added_step_count: int = 0


@dataclass
class TaskStepStarted(TaskDomainEvent):
    """规划中的某一步开始执行。"""

    step_id: StepId = field(default_factory=StepId)
    description: str = ""
    agent_role: AgentRole = AgentRole.EXECUTOR


@dataclass
class TaskStepCompleted(TaskDomainEvent):
    """规划中的某一步执行完成。"""

    step_id: StepId = field(default_factory=StepId)
    result: str = ""


@dataclass
class TaskStepFailed(TaskDomainEvent):
    """规划中的某一步执行失败。"""

    step_id: StepId = field(default_factory=StepId)
    error: str = ""


@dataclass
class TaskCompleted(TaskDomainEvent):
    """任务成功结束。"""

    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskFailed(TaskDomainEvent):
    """任务失败结束。"""

    error: str = ""


@dataclass
class TaskCancelled(TaskDomainEvent):
    """任务被取消。"""

    reason: str = ""
