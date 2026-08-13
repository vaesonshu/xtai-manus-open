"""FastAPI 应用入口：装配路由与生命周期。"""

from __future__ import annotations

from fastapi import FastAPI

from infrastructure import get_settings
from presentation.api.routes import api_router


def create_app() -> FastAPI:
    """应用工厂：创建并配置 FastAPI 实例。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.0.1",
    )

    app.include_router(api_router)

    @app.on_event("startup")
    async def on_startup() -> None:  # pragma: no cover - 启动钩子
        # 预热配置，确保 .env 已被加载
        _ = settings

    return app


app = create_app()
