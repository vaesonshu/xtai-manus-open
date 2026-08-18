"""全局异常处理器：将领域异常与框架异常映射为统一 JSON 响应。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.exceptions import DomainError
from presentation.api.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """构造统一错误响应体。"""
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI, *, debug: bool = False) -> None:
    """注册全局异常处理器，在应用工厂中调用一次即可。"""

    @app.exception_handler(DomainError)
    async def handle_domain_error(
        _request: Request,
        exc: DomainError,
    ) -> JSONResponse:
        # 领域异常直接映射为对应 HTTP 状态码
        return _error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # 保留 Pydantic 校验明细，便于前端定位字段问题
        return _error_response(
            code="request_validation_error",
            message="request validation failed",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        # 将 FastAPI 内置 HTTPException 也收敛到同一响应结构
        detail = exc.detail
        if isinstance(detail, str):
            message = detail
            details: dict[str, Any] = {}
        else:
            message = "http error"
            details = {"detail": detail}

        return _error_response(
            code="http_error",
            message=message,
            status_code=exc.status_code,
            details=details,
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        # 未捕获异常记录完整堆栈，对外仅暴露安全信息
        logger.exception("未处理的异常", exc_info=exc)
        message = str(exc) if debug else "internal server error"
        return _error_response(
            code="internal_server_error",
            message=message,
            status_code=500,
        )
