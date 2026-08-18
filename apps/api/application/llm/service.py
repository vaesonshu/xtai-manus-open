"""LLM 配置应用服务：获取与更新配置的用例编排。"""

from __future__ import annotations

from collections.abc import Callable

from application.llm.dto import LlmConfigDTO, UpdateLlmConfigCommand
from domain.llm.config import LlmConfig, LlmConfigProfile
from domain.ports import EventBus, LlmConfigRepository, LlmRuntimePort


class LlmConfigApplicationService:
    """LLM 配置用例服务。

    首次访问时若仓库无配置，将使用 ``default_config_factory`` 引导默认值并持久化。
    更新配置后会同步热加载运行时，供后台 LLM 调用使用最新参数。
    """

    def __init__(
        self,
        repository: LlmConfigRepository,
        runtime: LlmRuntimePort,
        event_bus: EventBus,
        default_config_factory: Callable[[], LlmConfig],
    ) -> None:
        self._repository = repository
        self._runtime = runtime
        self._event_bus = event_bus
        self._default_config_factory = default_config_factory

    def get_config(self) -> LlmConfigDTO:
        """获取当前 LLM 配置（API Key 脱敏）。"""
        config = self._ensure_config()
        return LlmConfigDTO.from_config(config)

    def update_config(self, command: UpdateLlmConfigCommand) -> LlmConfigDTO:
        """更新 LLM 配置并热加载运行时。"""
        profile = LlmConfigProfile.bootstrap(self._ensure_config())
        profile.update(
            provider=command.provider,
            model=command.model,
            api_key=command.api_key,
            base_url=command.base_url,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
            timeout_seconds=command.timeout_seconds,
            clear_max_tokens=command.clear_max_tokens,
        )

        self._repository.save(profile.config)
        self._runtime.reload(profile.config)

        for event in profile.pull_events():
            self._event_bus.publish(event)

        return LlmConfigDTO.from_config(profile.config)

    def _ensure_config(self) -> LlmConfig:
        """确保配置存在：仓库无记录时从环境默认值引导。"""
        stored = self._repository.get()
        if stored is not None:
            return stored

        bootstrap = self._default_config_factory()
        bootstrap.validate()
        self._repository.save(bootstrap)
        self._runtime.reload(bootstrap)
        return bootstrap
