"""PostgreSQL LLM 配置仓库实现。"""

from __future__ import annotations

from domain.llm.config import DEFAULT_LLM_CONFIG_ID, LlmConfig
from infrastructure.persistence.database import Database
from infrastructure.persistence.models import LlmConfigModel


def _to_entity(model: LlmConfigModel) -> LlmConfig:
    return LlmConfig(
        config_id=model.id,
        provider=model.provider,
        model=model.model,
        api_key=model.api_key,
        base_url=model.base_url,
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        timeout_seconds=model.timeout_seconds,
    )


def _apply_entity(model: LlmConfigModel, config: LlmConfig) -> None:
    model.provider = config.provider
    model.model = config.model
    model.api_key = config.api_key
    model.base_url = config.base_url
    model.temperature = config.temperature
    model.max_tokens = config.max_tokens
    model.timeout_seconds = config.timeout_seconds


class PostgresLlmConfigRepository:
    """基于 PostgreSQL 的 ``LlmConfigRepository`` 实现。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> LlmConfig | None:
        with self._database.session() as session:
            model = session.get(LlmConfigModel, DEFAULT_LLM_CONFIG_ID)
            if model is None:
                return None
            return _to_entity(model)

    def save(self, config: LlmConfig) -> None:
        with self._database.session() as session:
            model = session.get(LlmConfigModel, config.config_id)
            if model is None:
                model = LlmConfigModel(
                    id=config.config_id,
                    provider=config.provider,
                    model=config.model,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    timeout_seconds=config.timeout_seconds,
                )
                session.add(model)
            else:
                _apply_entity(model, config)
