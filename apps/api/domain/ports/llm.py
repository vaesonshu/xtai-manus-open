"""LLM 相关领域端口。"""

from __future__ import annotations

from typing import Protocol

from domain.llm.config import LlmConfig


class LlmConfigRepository(Protocol):
    """LLM 配置持久化端口。"""

    def get(self) -> LlmConfig | None:
        """读取当前配置；未初始化时返回 ``None``。"""
        ...

    def save(self, config: LlmConfig) -> None:
        """保存（新增或更新）配置。"""
        ...


class LlmRuntimePort(Protocol):
    """LLM 运行时端口：支持配置热更新与后台调用基础设施。

    具体 LangChain 客户端创建由基础设施层实现，领域层只关心配置生命周期。
    """

    def current_config(self) -> LlmConfig:
        """返回当前生效配置。"""
        ...

    def reload(self, config: LlmConfig) -> None:
        """热加载新配置（使后续调用使用最新参数）。"""
        ...
