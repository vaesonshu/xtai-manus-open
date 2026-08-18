"""LLM 配置应用服务与 API 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from application.llm.dto import UpdateLlmConfigCommand
from application.llm.service import LlmConfigApplicationService
from domain.llm.config import LlmConfig
from infrastructure.events import InMemoryEventBus
from infrastructure.llm.config_repository import InMemoryLlmConfigRepository
from infrastructure.llm.runtime import LlmRuntime
from main import create_app


def _build_service() -> LlmConfigApplicationService:
    default = LlmConfig.create(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-default",
        base_url="https://api.openai.com/v1",
        temperature=0.0,
    )
    runtime = LlmRuntime(default)
    return LlmConfigApplicationService(
        repository=InMemoryLlmConfigRepository(),
        runtime=runtime,
        event_bus=InMemoryEventBus(),
        default_config_factory=lambda: default,
    )


def test_get_config_bootstraps_from_default() -> None:
    service = _build_service()
    dto = service.get_config()
    assert dto.model == "gpt-4o-mini"
    assert dto.has_api_key is True
    assert "***" in dto.api_key_masked


def test_update_config_reloads_runtime() -> None:
    default = LlmConfig.create(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-default",
        base_url="https://api.openai.com/v1",
        temperature=0.0,
    )
    runtime = LlmRuntime(default)
    service = LlmConfigApplicationService(
        repository=InMemoryLlmConfigRepository(),
        runtime=runtime,
        event_bus=InMemoryEventBus(),
        default_config_factory=lambda: default,
    )
    service.get_config()
    updated = service.update_config(
        UpdateLlmConfigCommand(model="gpt-4o", temperature=0.2)
    )
    assert updated.model == "gpt-4o"
    assert updated.temperature == 0.2
    assert runtime.current_config().model == "gpt-4o"


def test_llm_config_api_get_and_put() -> None:
    client = TestClient(create_app())
    get_resp = client.get("/v1/llm/config")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["model"] == "gpt-4o-mini"
    assert "api_key" not in body

    put_resp = client.put(
        "/v1/llm/config",
        json={"model": "gpt-4o", "temperature": 0.5},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["model"] == "gpt-4o"
    assert put_resp.json()["temperature"] == 0.5
