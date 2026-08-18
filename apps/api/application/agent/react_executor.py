"""ReAct 执行器：LLM 与工具之间的迭代调用循环。"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from application.agent.config import AgentExecutionConfig
from application.agent.role_config import RoleConfig, get_role_config
from application.memory.service import MemoryApplicationService
from domain.agent.role import AgentRole
from domain.event import error_event, tool_called, tool_calling
from domain.event.base import StreamEvent
from domain.exceptions import ValidationError, WaitForUserInputError
from domain.memory.constants import MESSAGE_ASK_USER_TOOL
from domain.ports.llm import LlmRuntimePort
from domain.task.identifiers import TaskId
from domain.tool.result import ToolResult
from infrastructure.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

OnEventCallback = Callable[[StreamEvent], Awaitable[None]]


class ReActExecutor:
    """单 Agent 的 ReAct 执行循环，按角色配置 prompt 与工具。"""

    def __init__(
        self,
        *,
        llm_runtime: LlmRuntimePort,
        memory_service: MemoryApplicationService,
        tool_registry: ToolRegistry,
        config: AgentExecutionConfig | None = None,
    ) -> None:
        self._llm_runtime = llm_runtime
        self._memory = memory_service
        self._tools = tool_registry
        self._config = config or AgentExecutionConfig()

    async def invoke(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        query: str,
        on_event: OnEventCallback | None = None,
    ) -> str:
        """执行 ReAct 循环并返回最终文本结果。"""
        role_config = get_role_config(agent_role)
        await self._ensure_system_prompt(task_id, agent_role, role_config.system_prompt)
        await self._add_messages(task_id, agent_role, [{"role": "user", "content": query}])

        message = await self._invoke_llm(task_id, agent_role, role_config)
        return await self._run_tool_loop(
            task_id=task_id,
            agent_role=agent_role,
            role_config=role_config,
            message=message,
            on_event=on_event,
        )

    async def continue_after_user_input(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        on_event: OnEventCallback | None = None,
    ) -> str:
        """用户回复后继续 ReAct（调用方应已执行 ``rollback_for_user_input``）。"""
        role_config = get_role_config(agent_role)
        message = await self._invoke_llm(task_id, agent_role, role_config)
        return await self._run_tool_loop(
            task_id=task_id,
            agent_role=agent_role,
            role_config=role_config,
            message=message,
            on_event=on_event,
        )

    async def _run_tool_loop(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        role_config: RoleConfig,
        message: dict[str, Any],
        on_event: OnEventCallback | None,
    ) -> str:
        """工具调用迭代，直至 assistant 返回纯文本。"""
        for _ in range(self._config.max_iterations):
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                break

            tool_messages: list[dict[str, Any]] = []
            for tool_call in tool_calls[:1]:
                tool_call_id = tool_call.get("id") or str(uuid.uuid4())
                function = tool_call.get("function") or {}
                function_name = str(function.get("name", ""))
                function_args = self._parse_tool_arguments(function.get("arguments"))

                if function_name == MESSAGE_ASK_USER_TOOL:
                    question = self._extract_ask_user_question(function_args)
                    raise WaitForUserInputError(
                        "等待用户输入",
                        agent_role=agent_role,
                        question=question,
                    )

                tool = self._tools.resolve(function_name)

                if on_event is not None:
                    await on_event(
                        tool_calling(
                            tool_call_id=tool_call_id,
                            tool_name=tool.name,
                            function_name=function_name,
                            function_args=function_args,
                        )
                    )

                result = await self._invoke_tool(function_name, function_args)

                if on_event is not None:
                    await on_event(
                        tool_called(
                            tool_call_id=tool_call_id,
                            tool_name=tool.name,
                            function_name=function_name,
                            function_args=function_args,
                            function_result=result.to_tool_content(),
                        )
                    )

                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "function_name": function_name,
                        "content": result.to_tool_content(),
                    }
                )

            message = await self._invoke_llm(
                task_id,
                agent_role,
                role_config,
                extra_messages=tool_messages,
            )
        else:
            if on_event is not None:
                await on_event(
                    error_event(
                        f"Agent 迭代超过最大次数: {self._config.max_iterations}"
                    )
                )
            raise ValidationError("react iteration limit exceeded")

        content = str(message.get("content") or "").strip()
        if not content:
            raise ValidationError("agent returned empty content")
        return content

    async def _invoke_llm(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        role_config: RoleConfig,
        *,
        extra_messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if extra_messages:
            await self._add_messages(task_id, agent_role, extra_messages)

        provider = self._llm_runtime.get_provider()
        tools = self._tools.get_schemas(role_config.tool_names)
        response_format = role_config.response_format
        error = "调用语言模型发生错误"

        for _ in range(self._config.max_retries):
            try:
                conversation = self._memory.get_agent_conversation(task_id, agent_role)
                message = await provider.invoke(
                    messages=conversation.get_messages(),
                    tools=tools or None,
                    response_format=response_format,
                    tool_choice=role_config.tool_choice,
                )

                filtered = self._normalize_assistant_message(message)
                if not self._has_llm_output(filtered):
                    logger.warning("LLM 返回空内容，准备重试")
                    await asyncio.sleep(self._config.retry_interval)
                    continue

                await self._add_messages(task_id, agent_role, [filtered])
                return filtered
            except Exception as exc:  # noqa: BLE001
                logger.exception("ReAct LLM 调用失败")
                error = str(exc)
                await asyncio.sleep(self._config.retry_interval)

        raise ValidationError(
            f"调用语言模型失败，已达最大重试次数({self._config.max_retries}): {error}"
        )

    async def _invoke_tool(
        self,
        function_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        last_error = "tool invocation failed"
        for _ in range(self._config.max_retries):
            try:
                return await self._tools.invoke(function_name, arguments)
            except Exception as exc:  # noqa: BLE001
                logger.exception("工具调用失败: %s", function_name)
                last_error = str(exc)
                await asyncio.sleep(self._config.retry_interval)
        return ToolResult(success=False, message=last_error)

    async def _ensure_system_prompt(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        system_prompt: str,
    ) -> None:
        conversation = self._memory.get_agent_conversation(task_id, agent_role)
        if conversation.empty:
            self._memory.add_agent_message(
                task_id,
                agent_role,
                {"role": "system", "content": system_prompt},
            )

    async def _add_messages(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        messages: list[dict[str, Any]],
    ) -> None:
        for message in messages:
            self._memory.add_agent_message(task_id, agent_role, message)

    @staticmethod
    def _extract_ask_user_question(arguments: dict[str, Any]) -> str:
        """从 ``message_ask_user`` 参数中提取问题文本。"""
        for key in ("question", "text", "message", "content"):
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "请补充更多信息。"

    @staticmethod
    def _has_llm_output(message: dict[str, Any]) -> bool:
        """判断 LLM 响应是否包含可用内容（文本或工具调用）。"""
        content = str(message.get("content") or "").strip()
        tool_calls = message.get("tool_calls") or []
        return bool(content or tool_calls)

    @staticmethod
    def _normalize_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
        role = message.get("role")
        if role != "assistant":
            return dict(message)

        filtered: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content"),
        }
        if message.get("reasoning_content"):
            filtered["reasoning_content"] = message.get("reasoning_content")
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            filtered["tool_calls"] = tool_calls[:1]
        return filtered

    @staticmethod
    def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        if isinstance(raw, str):
            return json.loads(raw)
        raise ValidationError("invalid tool call arguments")
