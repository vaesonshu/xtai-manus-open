"""LLM 提供商端口：Agent 与 LLM 交互的抽象协议。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class LlmProviderPort(Protocol):
    """LLM 提供商端口。

    参考 OpenAI Chat Completions 语义，屏蔽具体 SDK 实现，
    使应用层与 Agent 编排仅依赖该协议。
    """

    @property
    def model_name(self) -> str:
        """当前使用的模型名称。"""
        ...

    @property
    def temperature(self) -> float:
        """采样温度。"""
        ...

    @property
    def max_tokens(self) -> int | None:
        """最大生成 token 数；``None`` 表示由服务端默认。"""
        ...

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        """调用 LLM 并返回 assistant 消息字典（含 content / tool_calls 等）。"""
        ...

    async def astream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式调用 LLM；中间块 partial=True，最后一块 partial=False。"""
        ...
