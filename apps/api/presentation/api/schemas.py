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
