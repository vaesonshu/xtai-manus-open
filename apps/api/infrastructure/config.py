"""应用配置：从环境变量 / .env 读取，用 pydantic-settings 校验。"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(value: Any) -> list[str]:
    """将环境变量中的逗号分隔字符串解析为来源列表。"""
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, list):
        return value
    raise TypeError("CORS_ORIGINS 必须是逗号分隔字符串或字符串列表")


# 支持 CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 形式
CorsOrigins = Annotated[list[str], BeforeValidator(_parse_cors_origins)]


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

    # CORS：默认放行本地 Next.js 开发服务器
    cors_origins: CorsOrigins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    cors_allow_credentials: bool = True

    # LLM
    openai_api_key: str = "sk-dummy"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0

    # LangGraph
    checkpoint_db_path: str = "./data/checkpoints.db"
    agent_max_iterations: int = 30
    # 是否调用 LLM 做在线规划（False 时使用离线三步规划）
    agent_use_llm_planning: bool = True

    # Storage
    data_dir: str = "./data"

    # Redis 缓存
    redis_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "xtai"
    redis_default_ttl: int = 300

    # PostgreSQL 业务数据库
    database_enabled: bool = True
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/xtai"
    database_echo: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "text" | "json"
    log_console_enabled: bool = True
    log_file_enabled: bool = True
    log_file_path: str = "./data/logs/app.log"
    log_file_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_file_backup_count: int = 5
    # 是否用彩色控制台输出（生产环境建议关闭）
    log_colors: bool = True


@lru_cache
def get_settings() -> Settings:
    """获取（缓存后的）配置单例。"""
    return Settings()
