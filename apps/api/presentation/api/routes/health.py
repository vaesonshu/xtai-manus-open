"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from infrastructure import Container
from infrastructure.persistence.checkpointer import get_checkpointer_info
from presentation.api.schemas import HealthResponse
from presentation.deps import get_container

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(container: Container = Depends(get_container)) -> HealthResponse:
    """服务健康检查。"""
    redis_status = container.cache_health()
    database_status = container.database_health()
    checkpoint_info = get_checkpointer_info(container.settings)
    checkpoint_status = f"{checkpoint_info.backend}:{checkpoint_info.detail}"

    overall_status = (
        "ok"
        if redis_status in ("ok", "disabled") and database_status in ("ok", "disabled")
        else "degraded"
    )
    return HealthResponse(
        status=overall_status,
        service=container.settings.app_name,
        env=container.settings.app_env,
        redis=redis_status,
        database=database_status,
        checkpoint=checkpoint_status,
        orchestrator=container.settings.agent_orchestrator,
    )
