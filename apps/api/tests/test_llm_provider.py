"""LLM 提供商与运行时测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.exceptions import ValidationError
from domain.llm.config import LlmConfig
from infrastructure.llm.provider_factory import create_llm_provider
from infrastructure.llm.providers.openai_provider import OpenAiLlmProvider
from infrastructure.llm.runtime import LlmRuntime


def test_create_llm_provider_openai_compatible() -> None:
    config = LlmConfig.create(
        provider="openai_compatible",
        model="deepseek-chat",
        api_key="sk-test",
        base_url="https://api.deepseek.com",
    )
    provider = create_llm_provider(config)
    assert isinstance(provider, OpenAiLlmProvider)
    assert provider.model_name == "deepseek-chat"


def test_create_llm_provider_rejects_unknown() -> None:
    config = LlmConfig(
        provider="anthropic",
        model="claude",
        api_key="sk-test",
        base_url="https://example.com",
    )
    with pytest.raises(ValidationError):
        create_llm_provider(config)


def test_runtime_reload_switches_provider_model() -> None:
    config = LlmConfig.create(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    runtime = LlmRuntime(config)
    assert runtime.get_provider().model_name == "gpt-4o-mini"

    runtime.reload(
        LlmConfig.create(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
    )
    assert runtime.get_provider().model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_openai_provider_invoke_returns_message() -> None:
    config = LlmConfig.create(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    provider = OpenAiLlmProvider(config)

    mock_message = MagicMock()
    mock_message.model_dump.return_value = {"role": "assistant", "content": "hello"}
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch.object(provider._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await provider.invoke([{"role": "user", "content": "Hi"}])

    assert result["content"] == "hello"
    mock_create.assert_awaited_once()
