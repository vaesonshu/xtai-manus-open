"""LLM 配置应用层 DTO。"""

from __future__ import annotations

from dataclasses import dataclass

from domain.llm.config import LlmConfig


@dataclass(frozen=True)
class UpdateLlmConfigCommand:
    """更新 LLM 配置的命令（``None`` 字段表示保持原值）。"""

    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    clear_max_tokens: bool = False


@dataclass(frozen=True)
class LlmConfigDTO:
    """LLM 配置只读视图（API Key 已脱敏）。"""

    config_id: str
    provider: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int | None
    timeout_seconds: float
    api_key_masked: str
    has_api_key: bool

    @classmethod
    def from_config(cls, config: LlmConfig) -> LlmConfigDTO:
        return cls(
            config_id=config.config_id,
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_seconds=config.timeout_seconds,
            api_key_masked=config.mask_api_key(),
            has_api_key=bool(config.api_key),
        )
