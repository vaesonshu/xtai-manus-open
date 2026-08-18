"""OpenAI 兼容 LLM 提供商实现。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
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
            request_kwargs = self._build_request_kwargs(
                messages=messages,
                tools=tools,
                response_format=response_format,
                tool_choice=tool_choice,
            )
            response = await self._client.chat.completions.create(**request_kwargs)
            message = response.choices[0].message.model_dump()
            logger.debug("LLM 响应: %s", message)
            return message
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM 调用失败: model=%s", self.model_name)
            raise LlmInvokeError(f"llm invoke failed: {exc}") from exc

    async def astream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式 Chat Completions：逐块推送累积文本，最后返回完整 assistant 消息。"""
        try:
            request_kwargs = self._build_request_kwargs(
                messages=messages,
                tools=tools,
                response_format=response_format,
                tool_choice=tool_choice,
            )
            request_kwargs["stream"] = True

            stream = await self._client.chat.completions.create(**request_kwargs)
            accumulated_content = ""
            tool_calls_by_index: dict[int, dict[str, Any]] = {}
            reasoning_content = ""

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue

                if getattr(delta, "reasoning_content", None):
                    reasoning_content += str(delta.reasoning_content)

                if delta.content:
                    accumulated_content += delta.content
                    yield {
                        "role": "assistant",
                        "content": accumulated_content,
                        "partial": True,
                    }

                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        index = tool_call.index
                        entry = tool_calls_by_index.setdefault(
                            index,
                            {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            },
                        )
                        if tool_call.id:
                            entry["id"] = tool_call.id
                        if tool_call.function:
                            if tool_call.function.name:
                                entry["function"]["name"] += tool_call.function.name
                            if tool_call.function.arguments:
                                entry["function"]["arguments"] += (
                                    tool_call.function.arguments
                                )

            final_message: dict[str, Any] = {
                "role": "assistant",
                "content": accumulated_content or None,
            }
            if reasoning_content:
                final_message["reasoning_content"] = reasoning_content
            if tool_calls_by_index:
                final_message["tool_calls"] = [
                    tool_calls_by_index[index]
                    for index in sorted(tool_calls_by_index)
                ]
            final_message["partial"] = False
            yield final_message
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM 流式调用失败: model=%s", self.model_name)
            raise LlmInvokeError(f"llm stream failed: {exc}") from exc

    def _build_request_kwargs(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, Any] | None,
        tool_choice: str | None,
    ) -> dict[str, Any]:
        """组装 Chat Completions 请求参数（invoke / astream 共用）。"""
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
            request_kwargs["parallel_tool_calls"] = False
        else:
            logger.info("LLM 请求未携带工具: model=%s", self.model_name)
        return request_kwargs
