"""LLM 配置领域模型：值对象与聚合根。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from domain.exceptions import ValidationError
from domain.llm.events import LlmConfigUpdated
from domain.primitives import IntegrationEvent

# 系统级默认配置 ID（单例配置）
DEFAULT_LLM_CONFIG_ID = "default"


@dataclass(frozen=True)
class LlmConfig:
    """LLM 连接配置值对象。

    封装模型、端点、鉴权等调用参数，可在运行期热更新。
    """

    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: float = 60.0
    config_id: str = DEFAULT_LLM_CONFIG_ID

    def validate(self) -> None:
        """校验配置不变量。"""
        if not self.provider.strip():
            raise ValidationError("provider must not be empty")
        if not self.model.strip():
            raise ValidationError("model must not be empty")
        if not self.api_key.strip():
            raise ValidationError("api_key must not be empty")
        if not self.base_url.strip():
            raise ValidationError("base_url must not be empty")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValidationError("temperature must be between 0.0 and 2.0")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValidationError("max_tokens must be positive when set")
        if self.timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be positive")

    @classmethod
    def create(
        cls,
        *,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        timeout_seconds: float = 60.0,
        config_id: str = DEFAULT_LLM_CONFIG_ID,
    ) -> LlmConfig:
        """工厂方法：创建并校验配置。"""
        config = cls(
            provider=provider.strip(),
            model=model.strip(),
            api_key=api_key.strip(),
            base_url=base_url.strip(),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            config_id=config_id,
        )
        config.validate()
        return config

    def mask_api_key(self) -> str:
        """返回脱敏后的 API Key，供对外展示。"""
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:3]}***{self.api_key[-4:]}"


@dataclass
class LlmConfigProfile:
    """LLM 配置聚合根（系统单例）。

    负责配置更新规则与 ``LlmConfigUpdated`` 领域事件发布。
    """

    config: LlmConfig
    _events: list[IntegrationEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def bootstrap(cls, config: LlmConfig) -> LlmConfigProfile:
        """从已有配置引导聚合根。"""
        return cls(config=config)

    def update(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        clear_max_tokens: bool = False,
    ) -> None:
        """按字段增量更新配置；``api_key=None`` 表示保留原密钥。"""
        updated = replace(
            self.config,
            provider=provider.strip() if provider is not None else self.config.provider,
            model=model.strip() if model is not None else self.config.model,
            api_key=api_key.strip() if api_key is not None else self.config.api_key,
            base_url=base_url.strip() if base_url is not None else self.config.base_url,
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=None if clear_max_tokens else (
                max_tokens if max_tokens is not None else self.config.max_tokens
            ),
            timeout_seconds=(
                timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
            ),
        )
        updated.validate()
        self.config = updated
        self._events.append(LlmConfigUpdated(config_id=updated.config_id))

    def pull_events(self) -> list[IntegrationEvent]:
        """取出并清空累积的集成事件。"""
        events = self._events
        self._events = []
        return events
