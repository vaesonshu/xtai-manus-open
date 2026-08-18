"""全局异常处理器测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import create_app


def test_not_found_returns_unified_error_body() -> None:
    """查询不存在的 run 应返回 404 与统一错误结构。"""
    client = TestClient(create_app())
    response = client.get("/v1/agents/runs/non-existent-id")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert "non-existent-id" in body["error"]["message"]


def test_validation_error_returns_unified_error_body() -> None:
    """请求体验证失败应返回 422 与字段错误明细。"""
    client = TestClient(create_app())
    response = client.post("/v1/agents/runs", json={"goal": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "request_validation_error"
    assert "errors" in body["error"]["details"]
