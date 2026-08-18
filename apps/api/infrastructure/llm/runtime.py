"""LLM 运行时：动态提供商、热更新与后台异步调用。"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from langchain_openai import ChatOpenAI

from domain.llm.config import LlmConfig
from domain.llm.provider import LlmProviderPort
from infrastructure.llm.provider_factory import create_llm_provider

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LlmRuntime:
    """LLM 运行时：管理可热更新的提供商实例与后台执行线程池。"""

    def __init__(self, initial_config: LlmConfig, *, max_workers: int = 4) -> None:
        self._lock = threading.RLock()
        self._config = initial_config
        self._provider: LlmProviderPort = create_llm_provider(initial_config)
        self._chat_client: ChatOpenAI | None = None
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="llm-worker",
        )

    def current_config(self) -> LlmConfig:
        with self._lock:
            return self._config

    def reload(self, config: LlmConfig) -> None:
        """热加载配置并重建提供商（后续 invoke 使用新参数）。"""
        config.validate()
        with self._lock:
            self._config = config
            self._provider = create_llm_provider(config)
            self._chat_client = None
        logger.info(
            "LLM 运行时已热加载 (provider=%s, model=%s)",
            config.provider,
            config.model,
        )

    def get_provider(self) -> LlmProviderPort:
        """获取当前 LLM 提供商实例。"""
        with self._lock:
            return self._provider

    async def ainvoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        """异步调用当前提供商。"""
        provider = self.get_provider()
        return await provider.invoke(
            messages=messages,
            tools=tools,
            response_format=response_format,
            tool_choice=tool_choice,
        )

    def submit_invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> Future[dict[str, Any]]:
        """在后台线程池中执行异步 LLM 调用，避免阻塞主线程。"""

        def _run() -> dict[str, Any]:
            return asyncio.run(
                self.ainvoke(
                    messages=messages,
                    tools=tools,
                    response_format=response_format,
                    tool_choice=tool_choice,
                )
            )

        return self._executor.submit(_run)

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
        """提交通用后台任务。"""
        return self._executor.submit(fn, *args, **kwargs)

    def get_chat_model(self) -> ChatOpenAI:
        """获取 LangChain ChatOpenAI 实例（供 LangGraph 节点复用）。"""
        with self._lock:
            if self._chat_client is None:
                self._chat_client = self._build_chat_client(self._config)
            return self._chat_client

    def shutdown(self) -> None:
        """关闭后台线程池。"""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _build_chat_client(self, config: LlmConfig) -> ChatOpenAI:
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
