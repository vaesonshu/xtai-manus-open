"""从应用配置构造默认 LLM 领域配置。"""

from __future__ import annotations

from domain.llm.config import LlmConfig
from infrastructure.config import Settings


def llm_config_from_settings(settings: Settings) -> LlmConfig:
    """将 ``Settings`` 中的 LLM 环境变量映射为领域配置。"""
    return LlmConfig.create(
        provider="openai",
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=settings.llm_temperature,
    )
