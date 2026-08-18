"""LLM 调用应用服务：编排运行时提供商调用。"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any

from domain.ports import LlmRuntimePort


class LlmInvokeApplicationService:
    """LLM 调用用例服务（供 Agent 或 API 层使用）。"""

    def __init__(self, runtime: LlmRuntimePort) -> None:
        self._runtime = runtime

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        """同步上下文中直接异步调用 LLM。"""
        provider = self._runtime.get_provider()
        return await provider.invoke(
            messages=messages,
            tools=tools,
            response_format=response_format,
            tool_choice=tool_choice,
        )

    def invoke_in_background(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> Future[dict[str, Any]]:
        """后台线程池调用 LLM（返回 ``Future``）。"""
        runtime = self._runtime
        if not hasattr(runtime, "submit_invoke"):
            raise RuntimeError("当前 LlmRuntime 未实现 submit_invoke")
        return runtime.submit_invoke(  # type: ignore[attr-defined]
            messages=messages,
            tools=tools,
            response_format=response_format,
            tool_choice=tool_choice,
        )
