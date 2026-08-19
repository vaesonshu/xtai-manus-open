"""表现层 API Schema：HTTP 请求/响应模型（Pydantic）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StartRunRequest(BaseModel):
    """发起运行的请求体。"""

    goal: str = Field(..., min_length=1, description="agent 要完成的目标")


class AgentRunResponse(BaseModel):
    """运行状态响应。"""

    run_id: str
    goal: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    service: str
    env: str
    redis: str = "disabled"
    database: str = "disabled"
    checkpoint: str = "disabled"
    orchestrator: str = "unknown"


class ErrorDetail(BaseModel):
    """错误详情（统一错误响应的内层结构）。"""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """统一错误响应体。"""

    error: ErrorDetail


class LlmConfigResponse(BaseModel):
    """LLM 配置响应（API Key 已脱敏）。"""

    config_id: str
    provider: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int | None = None
    timeout_seconds: float
    api_key_masked: str
    has_api_key: bool


class UpdateLlmConfigRequest(BaseModel):
    """更新 LLM 配置请求；未传字段表示保持原值。"""

    provider: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    api_key: str | None = Field(default=None, min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout_seconds: float | None = Field(default=None, gt=0)
    clear_max_tokens: bool = False


# --- Task API Schemas ---


class ReplyTaskRequest(BaseModel):
    """用户在 WAITING 状态下的回复。"""

    content: str = Field(..., min_length=1, description="用户回复内容")


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


# 流式事件 Schema 已迁移至 stream_event_schemas.py（discriminated union）
