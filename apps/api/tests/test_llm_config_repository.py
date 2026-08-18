"""PostgreSQL LLM 配置仓库测试。"""

from __future__ import annotations

from domain.llm.config import LlmConfig
from infrastructure.config import Settings
from infrastructure.persistence.database import Database
from infrastructure.persistence.llm_config_repository import PostgresLlmConfigRepository


def test_postgres_llm_config_repository_save_and_get() -> None:
    settings = Settings(
        database_enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
    )
    database = Database(settings)
    database.create_tables()
    repository = PostgresLlmConfigRepository(database)

    config = LlmConfig.create(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-repo-test",
        base_url="https://api.openai.com/v1",
    )
    repository.save(config)

    loaded = repository.get()
    assert loaded is not None
    assert loaded.model == "gpt-4o-mini"
    assert loaded.api_key == "sk-repo-test"
