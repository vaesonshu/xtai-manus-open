"""LLM 配置仓库：内存实现（测试 / 无数据库模式）。"""

from __future__ import annotations

from domain.llm.config import LlmConfig


class InMemoryLlmConfigRepository:
    """基于内存的 LLM 配置仓库。"""

    def __init__(self) -> None:
        self._config: LlmConfig | None = None

    def get(self) -> LlmConfig | None:
        return self._config

    def save(self, config: LlmConfig) -> None:
        self._config = config
