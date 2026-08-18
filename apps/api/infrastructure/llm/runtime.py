"""LLM 运行时：可热更新的 LangChain 客户端与后台执行线程池。"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from langchain_openai import ChatOpenAI

from domain.llm.config import LlmConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LlmRuntime:
    """LLM 运行时实现。

    - 配置变更时通过 ``reload`` 使客户端惰性重建
    - ``submit`` 提供后台线程池，避免阻塞 HTTP 请求（后续 agent 调用复用）
    """

    def __init__(self, initial_config: LlmConfig, *, max_workers: int = 4) -> None:
        self._lock = threading.RLock()
        self._config = initial_config
        self._client: ChatOpenAI | None = None
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="llm-worker",
        )

    def current_config(self) -> LlmConfig:
        with self._lock:
            return self._config

    def reload(self, config: LlmConfig) -> None:
        """热加载配置，并使缓存的 ChatOpenAI 客户端失效。"""
        config.validate()
        with self._lock:
            self._config = config
            self._client = None
        logger.info("LLM 运行时已热加载 (model=%s, base_url=%s)", config.model, config.base_url)

    def get_chat_model(self) -> ChatOpenAI:
        """获取当前配置对应的 LangChain ChatOpenAI 实例（惰性创建）。"""
        with self._lock:
            if self._client is None:
                self._client = self._build_client(self._config)
            return self._client

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
        """提交后台 LLM 相关任务，供异步 agent 执行链路使用。"""
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self) -> None:
        """关闭后台线程池。"""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _build_client(self, config: LlmConfig) -> ChatOpenAI:
        kwargs: dict[str, Any] = {
            "model": config.model,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "temperature": config.temperature,
            "timeout": config.timeout_seconds,
        }
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        return ChatOpenAI(**kwargs)
