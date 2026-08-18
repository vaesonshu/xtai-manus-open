"""OpenAI 兼容 LLM 提供商实现。"""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from domain.exceptions import LlmInvokeError
from domain.llm.config import LlmConfig

logger = logging.getLogger(__name__)


class OpenAiLlmProvider:
    """基于 OpenAI SDK 的 LLM 提供商（兼容 OpenAI 格式端点）。

    支持 DeepSeek、通义等 OpenAI 兼容 API，由 ``LlmConfig.base_url`` 决定。
    """

    def __init__(self, config: LlmConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def temperature(self) -> float:
        return self._config.temperature

    @property
    def max_tokens(self) -> int | None:
        return self._config.max_tokens

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        """发起 Chat Completions 请求并返回 assistant 消息。"""
        try:
            request_kwargs: dict[str, Any] = {
                "model": self.model_name,
                "temperature": self.temperature,
                "messages": messages,
                "timeout": self._config.timeout_seconds,
            }
            if self.max_tokens is not None:
                request_kwargs["max_tokens"] = self.max_tokens
            if response_format is not None:
                request_kwargs["response_format"] = response_format

            if tools:
                logger.info("LLM 请求携带工具: model=%s", self.model_name)
                request_kwargs["tools"] = tools
                if tool_choice is not None:
                    request_kwargs["tool_choice"] = tool_choice
                # 关闭并行工具调用，兼容部分 OpenAI 兼容端点
                request_kwargs["parallel_tool_calls"] = False
            else:
                logger.info("LLM 请求未携带工具: model=%s", self.model_name)

            response = await self._client.chat.completions.create(**request_kwargs)
            message = response.choices[0].message.model_dump()
            logger.debug("LLM 响应: %s", message)
            return message
        except Exception as exc:  # noqa: BLE001 - 统一映射为领域异常
            logger.exception("LLM 调用失败: model=%s", self.model_name)
            raise LlmInvokeError(f"llm invoke failed: {exc}") from exc
