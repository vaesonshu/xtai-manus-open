"""ReActExecutor 单元测试。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from application.agent.config import AgentExecutionConfig
from application.agent.react_executor import ReActExecutor
from application.memory.service import MemoryApplicationService
from domain.agent.role import AgentRole
from domain.exceptions import WaitForUserInputError
from domain.task.identifiers import TaskId
from infrastructure.json.repair_json_parser import RepairJsonParser
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.tools import MockToolKit, ToolRegistry
from infrastructure.tools.interaction_toolkit import build_interaction_toolkit


class ScriptedLlmProvider:
    """按脚本返回预设 assistant 消息，用于测试 ReAct 循环。"""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._index = 0

    @property
    def model_name(self) -> str:
        return "scripted"

    @property
    def temperature(self) -> float:
        return 0.0

    @property
    def max_tokens(self) -> int | None:
        return None

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        del messages, tools, response_format, tool_choice
        if self._index >= len(self._responses):
            return {"role": "assistant", "content": "fallback"}
        message = self._responses[self._index]
        self._index += 1
        return message

    async def astream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        final = await self.invoke(
            messages,
            tools=tools,
            response_format=response_format,
            tool_choice=tool_choice,
        )
        if final.get("tool_calls"):
            yield {**final, "partial": False}
            return
        content = str(final.get("content") or "")
        if not content:
            yield {**final, "partial": False}
            return
        for index in range(1, len(content) + 1):
            yield {"role": "assistant", "content": content[:index], "partial": True}
        yield {**final, "partial": False}


class ScriptedLlmRuntime:
    def __init__(self, provider: ScriptedLlmProvider) -> None:
        self._provider = provider

    def get_provider(self) -> ScriptedLlmProvider:
        return self._provider


def _build_executor(
    runtime: ScriptedLlmRuntime,
    memory_service: MemoryApplicationService,
    tool_registry: ToolRegistry,
    **config_kwargs: object,
) -> ReActExecutor:
    return ReActExecutor(
        llm_runtime=runtime,
        memory_service=memory_service,
        tool_registry=tool_registry,
        json_parser=RepairJsonParser(),
        config=AgentExecutionConfig(**config_kwargs),
    )


@pytest.mark.asyncio
async def test_react_executor_direct_answer() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider(
            [{"role": "assistant", "content": "调研完成，已收集公开资料。"}]
        )
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([MockToolKit()]),
        max_retries=1,
        retry_interval=0,
    )

    task_id = TaskId()
    result = await executor.invoke(
        task_id=task_id,
        agent_role=AgentRole.RESEARCHER,
        query="收集竞品资料",
    )
    assert result.result == "调研完成，已收集公开资料。"

    conversation = memory_service.get_agent_conversation(task_id, AgentRole.RESEARCHER)
    assert any(item.get("role") == "system" for item in conversation.get_messages())


@pytest.mark.asyncio
async def test_react_executor_structured_json_output() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    payload = {
        "success": True,
        "result": "已生成报告",
        "attachments": ["/workspace/report.md"],
    }
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider([{"role": "assistant", "content": json.dumps(payload)}])
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([MockToolKit()]),
        max_retries=1,
        retry_interval=0,
    )

    result = await executor.invoke(
        task_id=TaskId(),
        agent_role=AgentRole.CODER,
        query="生成报告",
    )
    assert result.success is True
    assert result.result == "已生成报告"
    assert result.attachments[0].filepath == "/workspace/report.md"
    assert result.attachments[0].filename == "report.md"


@pytest.mark.asyncio
async def test_react_executor_tool_loop_emits_events() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "echo",
                                "arguments": json.dumps({"text": "hello"}),
                            },
                        }
                    ],
                },
                {"role": "assistant", "content": "工具已执行，步骤完成。"},
            ]
        )
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([MockToolKit()]),
        max_retries=1,
        max_iterations=5,
        retry_interval=0,
    )

    events: list[str] = []

    async def on_event(event) -> None:
        events.append(event.type)

    task_id = TaskId()
    result = await executor.invoke(
        task_id=task_id,
        agent_role=AgentRole.RESEARCHER,
        query="测试工具调用",
        on_event=on_event,
    )

    assert result.result == "工具已执行，步骤完成。"
    assert events.count("tool") == 2
    assert "message" in events


@pytest.mark.asyncio
async def test_react_executor_empty_response_retries() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider(
            [
                {"role": "assistant", "content": ""},
                {"role": "assistant", "content": "重试后获得有效回复。"},
            ]
        )
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([MockToolKit()]),
        max_retries=3,
        retry_interval=0,
    )

    result = await executor.invoke(
        task_id=TaskId(),
        agent_role=AgentRole.REVIEWER,
        query="测试空回复重试",
    )
    assert result.result == "重试后获得有效回复。"


@pytest.mark.asyncio
async def test_react_executor_message_ask_user_raises_wait() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-ask",
                            "type": "function",
                            "function": {
                                "name": "message_ask_user",
                                "arguments": '{"text": "请确认目标？"}',
                            },
                        }
                    ],
                }
            ]
        )
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([build_interaction_toolkit()]),
        max_retries=1,
        retry_interval=0,
    )

    with pytest.raises(WaitForUserInputError) as exc_info:
        await executor.invoke(
            task_id=TaskId(),
            agent_role=AgentRole.RESEARCHER,
            query="需要用户确认",
        )

    assert exc_info.value.question == "请确认目标？"
    assert exc_info.value.agent_role is AgentRole.RESEARCHER


@pytest.mark.asyncio
async def test_react_executor_streams_partial_messages() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider([{"role": "assistant", "content": "流式回复内容"}])
    )
    executor = _build_executor(
        runtime,
        memory_service,
        ToolRegistry([MockToolKit()]),
        max_retries=1,
        retry_interval=0,
    )

    partial_flags: list[bool] = []
    messages: list[str] = []

    async def on_event(event) -> None:
        if event.type != "message":
            return
        partial_flags.append(bool(getattr(event, "partial", False)))
        messages.append(event.message)

    await executor.invoke(
        task_id=TaskId(),
        agent_role=AgentRole.RESEARCHER,
        query="测试流式",
        on_event=on_event,
    )

    assert any(partial_flags)
    assert partial_flags[-1] is False
    assert messages[-1] == "流式回复内容"
    assert len(messages) > 1
