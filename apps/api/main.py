"""FastAPI 应用入口：装配路由与生命周期。"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure import get_settings
from infrastructure.logging_ import setup_logging
from presentation.api.routes import api_router
from presentation.exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """应用工厂：创建并配置 FastAPI 实例。"""
    settings = get_settings()

    # 在应用创建时即初始化日志，确保请求日志与启动日志都被正确格式化
    setup_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.0.1",
    )

    # 跨域中间件需在路由注册前挂载，以便预检 OPTIONS 请求也能被正确处理
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app, debug=settings.debug)

    app.include_router(api_router)

    @app.on_event("startup")
    async def on_startup() -> None:  # pragma: no cover - 启动钩子
        logger.info("服务启动完成 (env=%s, level=%s)", settings.app_env, settings.log_level)

    return app


app = create_app()
