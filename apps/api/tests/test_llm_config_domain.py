"""LLM 领域模型测试。"""

from __future__ import annotations

import pytest

from domain.exceptions import ValidationError
from domain.llm.config import LlmConfig, LlmConfigProfile
from domain.llm.events import LlmConfigUpdated


def test_llm_config_validate_temperature_range() -> None:
    with pytest.raises(ValidationError):
        LlmConfig.create(
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            temperature=3.0,
        )


def test_llm_config_profile_update_emits_event() -> None:
    profile = LlmConfigProfile.bootstrap(
        LlmConfig.create(
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-test-key",
            base_url="https://api.openai.com/v1",
        )
    )
    profile.update(model="gpt-4o")
    events = profile.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], LlmConfigUpdated)
    assert profile.config.model == "gpt-4o"
    assert profile.config.api_key == "sk-test-key"
