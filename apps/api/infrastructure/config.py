"""应用配置：从环境变量 / .env 读取，用 pydantic-settings 校验。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。所有值均可通过环境变量或 ``.env`` 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "xtai-api"
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LLM
    openai_api_key: str = "sk-dummy"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0

    # LangGraph
    checkpoint_db_path: str = "./data/checkpoints.db"
    agent_max_iterations: int = 30

    # Storage
    data_dir: str = "./data"


@lru_cache
def get_settings() -> Settings:
    """获取（缓存后的）配置单例。"""
    return Settings()
