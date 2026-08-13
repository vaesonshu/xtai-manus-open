"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from infrastructure import Container
from presentation.api.schemas import HealthResponse
from presentation.deps import get_container

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(container: Container = Depends(get_container)) -> HealthResponse:
    """服务健康检查。"""
    return HealthResponse(
        status="ok",
        service=container.settings.app_name,
        env=container.settings.app_env,
    )
