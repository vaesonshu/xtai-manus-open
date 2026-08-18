"""LLM 相关领域端口。"""

from __future__ import annotations

from typing import Protocol

from domain.llm.config import LlmConfig
from domain.llm.provider import LlmProviderPort


class LlmConfigRepository(Protocol):
    """LLM 配置持久化端口。"""

    def get(self) -> LlmConfig | None:
        """读取当前配置；未初始化时返回 ``None``。"""
        ...

    def save(self, config: LlmConfig) -> None:
        """保存（新增或更新）配置。"""
        ...


class LlmRuntimePort(Protocol):
    """LLM 运行时端口：支持配置热更新、提供商切换与后台调用。"""

    def current_config(self) -> LlmConfig:
        """返回当前生效配置。"""
        ...

    def reload(self, config: LlmConfig) -> None:
        """热加载新配置（重建底层提供商实例）。"""
        ...

    def get_provider(self) -> LlmProviderPort:
        """获取当前配置对应的 LLM 提供商实例。"""
        ...
