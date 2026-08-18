"""LLM 提供商工厂：根据动态配置实例化具体提供商。"""

from __future__ import annotations

from collections.abc import Callable

from domain.exceptions import ValidationError
from domain.llm.config import LlmConfig
from domain.llm.constants import SUPPORTED_LLM_PROVIDERS
from domain.llm.provider import LlmProviderPort
from infrastructure.llm.providers.openai_provider import OpenAiLlmProvider

ProviderBuilder = Callable[[LlmConfig], LlmProviderPort]

# 提供商注册表：新增提供商时在此注册 builder
_PROVIDER_REGISTRY: dict[str, ProviderBuilder] = {
    "openai": OpenAiLlmProvider,
    "openai_compatible": OpenAiLlmProvider,
}


def register_llm_provider(name: str, builder: ProviderBuilder) -> None:
    """注册自定义 LLM 提供商（用于扩展或测试）。"""
    _PROVIDER_REGISTRY[name.lower()] = builder


def create_llm_provider(config: LlmConfig) -> LlmProviderPort:
    """根据 ``LlmConfig.provider`` 创建对应的 LLM 提供商实例。"""
    provider_key = config.provider.lower()
    if provider_key not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise ValidationError(
            f"unsupported provider: {config.provider} (supported: {supported})"
        )

    builder = _PROVIDER_REGISTRY.get(provider_key)
    if builder is None:
        raise ValidationError(f"provider not registered: {config.provider}")

    return builder(config)
