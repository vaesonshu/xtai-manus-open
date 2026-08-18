"""Task 领域模型到 API Schema 的映射。"""

from __future__ import annotations

from domain.task.plan import TaskPlan
from domain.task.plan_snapshot import PlanSnapshot
from domain.task.step import TaskStep
from domain.task.task import AgentTask
from presentation.api.schemas import (
    PlanSnapshotSchema,
    ReplyTaskRequest,
    StartTaskRequest,
    TaskPlanSchema,
    TaskResponse,
    TaskStepSchema,
)


def to_task_step_schema(step: TaskStep) -> TaskStepSchema:
    """步骤实体转 API Schema。"""
    return TaskStepSchema(
        step_id=str(step.step_id),
        description=step.description,
        agent_role=step.agent_role.value,
        status=step.status.value,
        result=step.result,
        error=step.error,
    )


def to_task_plan_schema(plan: TaskPlan) -> TaskPlanSchema:
    """规划实体转 API Schema。"""
    return TaskPlanSchema(
        plan_id=str(plan.plan_id),
        title=plan.title,
        goal=plan.goal,
        message=plan.message,
        status=plan.status.value,
        steps=[to_task_step_schema(step) for step in plan.steps],
    )


def to_plan_snapshot_schema(snapshot: PlanSnapshot) -> PlanSnapshotSchema:
    """规划快照转 API Schema。"""
    return PlanSnapshotSchema(
        version=snapshot.version,
        plan_id=str(snapshot.plan_id),
        title=snapshot.title,
        goal=snapshot.goal,
        reason=snapshot.reason,
        steps=list(snapshot.steps),
    )


def to_task_response(task: AgentTask) -> TaskResponse:
    """任务聚合根转 API Schema。"""
    return TaskResponse(
        task_id=str(task.task_id),
        goal=task.goal,
        status=task.status.value,
        plan=to_task_plan_schema(task.plan) if task.plan else None,
        plan_versions=[
            to_plan_snapshot_schema(item) for item in task.plan_history
        ],
        result=dict(task.result),
        error=task.error,
    )
