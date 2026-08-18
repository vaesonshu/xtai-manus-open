"""领域异常：表达业务规则违反，由表现层映射为 HTTP 状态码。"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """领域异常基类。

    子类通过 ``code`` 与 ``status_code`` 描述错误语义，表现层据此生成统一响应。
    """

    code: str = "domain_error"
    status_code: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    """输入或前置条件不满足（如空 goal）。"""

    code = "validation_error"
    status_code = 422


class NotFoundError(DomainError):
    """请求的资源不存在。"""

    code = "not_found"
    status_code = 404


class ConflictError(DomainError):
    """当前状态不允许执行该操作（如非法状态流转）。"""

    code = "conflict"
    status_code = 409
