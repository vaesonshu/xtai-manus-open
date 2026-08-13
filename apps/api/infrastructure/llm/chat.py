"""LLM adapter: wraps LangChain ChatOpenAI creation.

Supports any OpenAI-compatible endpoint, just set base_url.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from infrastructure.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """Create (cached) chat model instance."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=settings.llm_temperature,
    )
