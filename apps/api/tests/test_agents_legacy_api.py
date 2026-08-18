"""遗留 /v1/agents/runs API 薄封装测试。"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from main import create_app
from presentation.deps import get_container
from tests.test_task_api import _build_test_container


def test_agents_runs_delegates_to_tasks() -> None:
    """POST /v1/agents/runs 应创建真实 Task 并可查询。"""
    container = _build_test_container(offline=True)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container

    with TestClient(app) as client:
        response = client.post("/v1/agents/runs", json={"goal": "遗留 API 测试"})
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        assert run_id

        for _ in range(100):
            get_resp = client.get(f"/v1/agents/runs/{run_id}")
            if get_resp.status_code == 200 and get_resp.json()["status"] == "completed":
                break
            time.sleep(0.02)

        final = client.get(f"/v1/agents/runs/{run_id}").json()
        assert final["status"] == "completed"
        assert final["goal"] == "遗留 API 测试"


def test_langgraph_mermaid_endpoint() -> None:
    """LangGraph 模式下可导出 Mermaid。"""
    container = _build_test_container(offline=True)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container

    with TestClient(app) as client:
        response = client.get("/v1/system/langgraph/mermaid")
        assert response.status_code == 200
        assert "graph TD" in response.text
        assert "execute_step" in response.text
