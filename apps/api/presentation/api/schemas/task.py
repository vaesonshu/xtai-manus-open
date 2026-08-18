"""Task 相关 API Schema（Pydantic）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StartTaskRequest(BaseModel):
    """发起 Agent 任务请求。"""

    goal: str = Field(..., min_length=1, description="任务目标")


class TaskStepSchema(BaseModel):
    """规划步骤响应片段。"""

    step_id: str
    description: str
    agent_role: str
    status: str
    result: str | None = None
    error: str | None = None


class TaskPlanSchema(BaseModel):
    """任务规划响应片段。"""

    plan_id: str
    title: str
    goal: str
    message: str = ""
    status: str
    steps: list[TaskStepSchema] = Field(default_factory=list)


class PlanSnapshotSchema(BaseModel):
    """规划版本快照。"""

    version: int
    plan_id: str
    title: str
    goal: str
    reason: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)


class TaskResponse(BaseModel):
    """任务状态响应。"""

    task_id: str
    goal: str
    status: str
    plan: TaskPlanSchema | None = None
    plan_versions: list[PlanSnapshotSchema] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class StreamEventSchema(BaseModel):
    """SSE / Redis Stream 推送事件（与 ``domain/event`` 序列化格式对齐）。"""

    id: str
    type: Literal["plan", "step", "message", "tool", "title", "wait", "error", "done"]
    created_at: str
    # 以下字段按 type 可选出现
    status: str | None = None
    plan: dict[str, Any] | None = None
    step: dict[str, Any] | None = None
    role: Literal["user", "assistant"] | None = None
    message: str | None = None
    attachments: list[dict[str, Any]] | None = None
    title: str | None = None
    error: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    function_name: str | None = None
    function_args: dict[str, Any] | None = None
    function_result: Any | None = None

    model_config = {"extra": "allow"}
