"""ReActExecutor 单元测试。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from application.agent.config import AgentExecutionConfig
from application.agent.react_executor import ReActExecutor
from application.memory.service import MemoryApplicationService
from domain.agent.role import AgentRole
from domain.task.identifiers import TaskId
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.tools import MockToolKit, ToolRegistry


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


class ScriptedLlmRuntime:
    def __init__(self, provider: ScriptedLlmProvider) -> None:
        self._provider = provider

    def get_provider(self) -> ScriptedLlmProvider:
        return self._provider


@pytest.mark.asyncio
async def test_react_executor_direct_answer() -> None:
    memory_service = MemoryApplicationService(InMemoryMemoryStoreRepository())
    runtime = ScriptedLlmRuntime(
        ScriptedLlmProvider(
            [{"role": "assistant", "content": "调研完成，已收集公开资料。"}]
        )
    )
    executor = ReActExecutor(
        llm_runtime=runtime,
        memory_service=memory_service,
        tool_registry=ToolRegistry([MockToolKit()]),
        config=AgentExecutionConfig(max_retries=1, retry_interval=0),
    )

    task_id = TaskId()
    result = await executor.invoke(
        task_id=task_id,
        agent_role=AgentRole.RESEARCHER,
        query="收集竞品资料",
    )
    assert result == "调研完成，已收集公开资料。"

    conversation = memory_service.get_agent_conversation(task_id, AgentRole.RESEARCHER)
    assert any(item.get("role") == "system" for item in conversation.get_messages())


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
    executor = ReActExecutor(
        llm_runtime=runtime,
        memory_service=memory_service,
        tool_registry=ToolRegistry([MockToolKit()]),
        config=AgentExecutionConfig(max_retries=1, max_iterations=5, retry_interval=0),
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

    assert result == "工具已执行，步骤完成。"
    assert events == ["tool", "tool"]
