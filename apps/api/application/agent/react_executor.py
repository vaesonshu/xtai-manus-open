"""ReAct 执行器：LLM 与工具之间的迭代调用循环。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from application.agent.config import AgentExecutionConfig
from application.agent.role_config import RoleConfig, get_role_config
from application.agent.schemas import StepExecutionOutput, SummarizeOutput
from application.agent.step_result import StepExecutionResult, SummarizeResult
from application.memory.service import MemoryApplicationService
from domain.agent.role import AgentRole
from domain.event.tool_content import build_tool_content
from domain.event import assistant_message, error_event, tool_called, tool_calling
from domain.event.base import StreamEvent
from domain.exceptions import ValidationError, WaitForUserInputError
from domain.file.attachment import FileAttachment, from_path_strings
from domain.memory.constants import MESSAGE_ASK_USER_TOOL
from domain.ports.json_parser import JsonParserPort
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
        json_parser: JsonParserPort,
        config: AgentExecutionConfig | None = None,
    ) -> None:
        self._llm_runtime = llm_runtime
        self._memory = memory_service
        self._tools = tool_registry
        self._json_parser = json_parser
        self._config = config or AgentExecutionConfig()
        self._active_stream_id: str | None = None

    async def invoke(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        query: str,
        on_event: OnEventCallback | None = None,
    ) -> StepExecutionResult:
        """执行 ReAct 循环并返回结构化步骤结果。"""
        role_config = get_role_config(agent_role)
        self._active_stream_id = str(uuid.uuid4()) if on_event is not None else None
        await self._ensure_system_prompt(task_id, agent_role, role_config.system_prompt)
        await self._add_messages(task_id, agent_role, [{"role": "user", "content": query}])

        message = await self._invoke_llm(
            task_id, agent_role, role_config, on_event=on_event
        )
        content, compact_facts = await self._run_tool_loop(
            task_id=task_id,
            agent_role=agent_role,
            role_config=role_config,
            message=message,
            on_event=on_event,
        )
        result = await self._parse_step_output(content)
        result = self._prefer_compact_tool_facts(result, compact_facts)
        await self._emit_final_assistant_message(on_event, result.display_text)
        return result

    async def continue_after_user_input(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        on_event: OnEventCallback | None = None,
    ) -> StepExecutionResult:
        """用户回复后继续 ReAct（调用方应已执行 ``rollback_for_user_input``）。"""
        role_config = get_role_config(agent_role)
        self._active_stream_id = str(uuid.uuid4()) if on_event is not None else None
        message = await self._invoke_llm(
            task_id, agent_role, role_config, on_event=on_event
        )
        content, compact_facts = await self._run_tool_loop(
            task_id=task_id,
            agent_role=agent_role,
            role_config=role_config,
            message=message,
            on_event=on_event,
        )
        result = await self._parse_step_output(content)
        result = self._prefer_compact_tool_facts(result, compact_facts)
        await self._emit_final_assistant_message(on_event, result.display_text)
        return result

    async def summarize(
        self,
        *,
        task_id: TaskId,
        goal: str,
        agent_role: AgentRole = AgentRole.COORDINATOR,
        on_event: OnEventCallback | None = None,
        deliverables: str = "",
    ) -> SummarizeResult:
        """任务完成后汇总历史上下文并生成交付结果。"""
        deliverable_text = deliverables.strip()
        # 计算结果等短答案：直接交付，禁止二次扩写成解释性长文
        if self._looks_like_compact_answer(deliverable_text):
            self._active_stream_id = (
                str(uuid.uuid4()) if on_event is not None else None
            )
            await self._emit_final_assistant_message(on_event, deliverable_text)
            return SummarizeResult(message=deliverable_text)

        from application.prompts.react import SUMMARIZE_PROMPT

        role_config = get_role_config(agent_role)
        context = self._memory.build_context(task_id)
        deliverable_block = deliverable_text or "(无)"
        query = (
            f"{SUMMARIZE_PROMPT.strip()}\n\n"
            f"任务目标：{goal}\n\n"
            f"各步骤已产出的交付内容（必须完整纳入最终 message）：\n{deliverable_block}\n\n"
            f"执行上下文：\n{context or '(无)'}"
        )
        await self._ensure_system_prompt(task_id, agent_role, role_config.system_prompt)
        await self._add_messages(task_id, agent_role, [{"role": "user", "content": query}])

        self._active_stream_id = str(uuid.uuid4()) if on_event is not None else None
        message = await self._invoke_llm(
            task_id,
            agent_role,
            role_config,
            tool_choice_override="none",
            on_event=on_event,
        )
        content = str(message.get("content") or "").strip()
        if not content:
            raise ValidationError("summarize returned empty content")
        result = await self._parse_summarize_output(content)
        final_message = self._resolve_summary_message(
            result.message,
            deliverables=deliverable_text,
        )
        await self._emit_final_assistant_message(
            on_event,
            final_message,
            attachments=list(result.attachments),
        )
        return SummarizeResult(
            message=final_message,
            attachments=result.attachments,
        )

    @staticmethod
    def _looks_like_compact_answer(text: str) -> bool:
        """短而具体的答案（如计算结果）应保留，不能被更长的步骤废话覆盖。"""
        stripped = text.strip()
        if not stripped or len(stripped) > 80:
            return False
        return any(ch.isdigit() for ch in stripped)

    @staticmethod
    def _is_hollow_summary(text: str) -> bool:
        """识别「已完成/希望您愉快」类空话收尾。"""
        stripped = text.strip()
        if not stripped or len(stripped) > 80:
            return False
        hollow_prefixes = (
            "已完成",
            "希望",
            "祝您",
            "如有",
            "任务已",
            "好的",
            "完成了",
            "done",
            "completed",
        )
        lower = stripped.lower()
        return any(
            stripped.startswith(prefix) or lower.startswith(prefix)
            for prefix in hollow_prefixes
        )

    @classmethod
    def _resolve_summary_message(cls, message: str, *, deliverables: str) -> str:
        """合并汇总文案与步骤交付物：保留短答案，仅在空话时用交付物兜底。"""
        final_message = message.strip()
        deliverable_text = deliverables.strip()
        if not final_message:
            return deliverable_text
        if not deliverable_text:
            return final_message

        # 空话收尾 + 有更实在的交付物 → 用交付物
        if cls._is_hollow_summary(final_message) and len(deliverable_text) > len(
            final_message
        ):
            return deliverable_text

        # 计算题等短答案：即使短于阈值也必须保留
        if cls._looks_like_compact_answer(final_message):
            return final_message

        min_len = max(120, int(len(deliverable_text) * 0.3))
        if len(final_message) < min_len and deliverable_text not in final_message:
            # 汇总偏短且未包含交付细节时拼接，避免丢掉步骤正文
            return f"{final_message}\n\n{deliverable_text}"
        if (
            deliverable_text not in final_message
            and len(deliverable_text) > len(final_message)
        ):
            return f"{final_message}\n\n{deliverable_text}"
        return final_message
    async def _run_tool_loop(
        self,
        *,
        task_id: TaskId,
        agent_role: AgentRole,
        role_config: RoleConfig,
        message: dict[str, Any],
        on_event: OnEventCallback | None,
    ) -> tuple[str, list[str]]:
        """工具调用迭代，直至 assistant 返回最终文本。

        同时收集 calculate / get_current_time 等短事实，供步骤结果兜底。
        """
        compact_facts: list[str] = []
        for _ in range(self._config.max_iterations):
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                break

            tool_messages: list[dict[str, Any]] = []
            for tool_call in tool_calls[:1]:
                tool_call_id = tool_call.get("id") or str(uuid.uuid4())
                function = tool_call.get("function") or {}
                function_name = str(function.get("name", ""))
                function_args = await self._parse_tool_arguments(function.get("arguments"))

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
                fact = self._compact_fact_from_tool(function_name, result)
                if fact:
                    compact_facts.append(fact)

                if on_event is not None:
                    await on_event(
                        tool_called(
                            tool_call_id=tool_call_id,
                            tool_name=tool.name,
                            function_name=function_name,
                            function_args=function_args,
                            function_result=self._serialize_tool_result(result),
                            tool_content=build_tool_content(
                                function_name,
                                function_args,
                                result,
                            ),
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
                on_event=on_event,
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
        return content, compact_facts

    @classmethod
    def _compact_fact_from_tool(
        cls, function_name: str, result: ToolResult
    ) -> str | None:
        """从工具结果提取可直接交付的短事实（计算结果、当前时间等）。"""
        if not result.success:
            return None
        if function_name not in {"calculate", "get_current_time"}:
            return None
        text = (result.message or "").strip()
        return text or None

    @classmethod
    def _prefer_compact_tool_facts(
        cls,
        result: StepExecutionResult,
        compact_facts: list[str],
    ) -> StepExecutionResult:
        """模型 result 未带回工具结论时，用工具短事实覆盖展示文案。"""
        if not compact_facts:
            return result
        display = (result.display_text or "").strip()
        missing = [fact for fact in compact_facts if fact not in display]
        if not missing:
            return result
        # 优先用最近一次短事实（如 4053）；展示文案若是进度废话则直接替换
        preferred = missing[-1]
        if cls._looks_like_compact_answer(preferred) and (
            not display
            or len(display) > 80
            or not cls._looks_like_compact_answer(display)
        ):
            return StepExecutionResult(
                success=result.success,
                result=preferred,
                attachments=result.attachments,
                raw_content=result.raw_content,
            )
        return result

    async def _invoke_llm(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        role_config: RoleConfig,
        *,
        extra_messages: list[dict[str, Any]] | None = None,
        tool_choice_override: str | None = None,
        on_event: OnEventCallback | None = None,
    ) -> dict[str, Any]:
        if extra_messages:
            await self._add_messages(task_id, agent_role, extra_messages)

        provider = self._llm_runtime.get_provider()
        tools = self._tools.get_schemas(role_config.tool_names)
        tool_choice = tool_choice_override or role_config.tool_choice
        # OpenAI json_object 与 tool_calls 互斥，工具循环阶段必须关闭
        response_format = self._effective_response_format(
            tools=tools or None,
            response_format=role_config.response_format,
            tool_choice=tool_choice,
        )
        error = "调用语言模型发生错误"
        use_stream = on_event is not None and hasattr(provider, "astream")

        for _ in range(self._config.max_retries):
            try:
                conversation = self._memory.get_agent_conversation(task_id, agent_role)
                if use_stream:
                    message = await self._invoke_llm_stream(
                        provider=provider,
                        messages=conversation.get_messages(),
                        tools=tools or None,
                        response_format=response_format,
                        tool_choice=tool_choice,
                        on_event=on_event,
                    )
                else:
                    message = await provider.invoke(
                        messages=conversation.get_messages(),
                        tools=tools or None,
                        response_format=response_format,
                        tool_choice=tool_choice,
                    )

                filtered = self._normalize_assistant_message(message)
                if not self._has_llm_output(filtered):
                    logger.warning("LLM 返回空内容，准备重试")
                    await self._add_messages(
                        task_id,
                        agent_role,
                        [
                            {"role": "assistant", "content": ""},
                            {"role": "user", "content": "AI无响应内容，请继续。"},
                        ],
                    )
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

    async def _invoke_llm_stream(
        self,
        *,
        provider: Any,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, Any] | None,
        tool_choice: str | None,
        on_event: OnEventCallback | None,
    ) -> dict[str, Any]:
        """通过 LLM.astream 流式输出，并向 SSE 推送 partial 消息。

        JSON 模式下不推送 partial：原始 token 是 schema 外壳，用户应只看到
        解析后的最终 message（由 ``_emit_final_assistant_message`` 发出）。
        """
        stream_id = self._active_stream_id or str(uuid.uuid4())
        self._active_stream_id = stream_id
        final_message: dict[str, Any] = {"role": "assistant", "content": ""}
        # json_object 流式内容是 {"message":...} 之类，推给前端会卡住「生成中」
        suppress_partial = (
            isinstance(response_format, dict)
            and response_format.get("type") == "json_object"
        )

        async for chunk in provider.astream(
            messages=messages,
            tools=tools,
            response_format=response_format,
            tool_choice=tool_choice,
        ):
            if chunk.get("partial"):
                text = str(chunk.get("content") or "")
                if text and on_event is not None and not suppress_partial:
                    await on_event(
                        assistant_message(text, partial=True, stream_id=stream_id)
                    )
                continue

            final_message = {
                key: value for key, value in chunk.items() if key != "partial"
            }

        if final_message.get("tool_calls"):
            return final_message

        content = str(final_message.get("content") or "")
        if content and on_event is not None and not suppress_partial:
            await on_event(
                assistant_message(content, partial=True, stream_id=stream_id)
            )
        return final_message

    async def _emit_final_assistant_message(
        self,
        on_event: OnEventCallback | None,
        message: str,
        *,
        attachments: list[FileAttachment] | None = None,
    ) -> None:
        """推送解析后的最终助手消息，替换流式中间帧。"""
        if on_event is None or not message.strip():
            return
        stream_id = self._active_stream_id or str(uuid.uuid4())
        await on_event(
            assistant_message(
                message,
                partial=False,
                stream_id=stream_id,
                attachments=attachments,
            )
        )
        self._active_stream_id = None

    @staticmethod
    def _serialize_tool_result(result: ToolResult) -> Any:
        """将工具结果转为 SSE 友好的 JSON 对象（前端可直接解析）。"""
        import json

        raw = result.to_tool_content()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    @staticmethod
    def _effective_response_format(
        *,
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, Any] | None,
        tool_choice: str | None,
    ) -> dict[str, Any] | None:
        """有工具可调用时禁用 JSON 模式，否则模型不会发起 tool_calls。"""
        if not tools:
            return response_format
        if tool_choice == "none":
            return response_format
        return None

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

    async def _parse_step_output(self, content: str) -> StepExecutionResult:
        """将 LLM 最终输出解析为结构化步骤结果。"""
        try:
            parsed = await self._json_parser.invoke(content)
            output = StepExecutionOutput.model_validate(parsed)
            return StepExecutionResult(
                success=output.success,
                result=output.result,
                attachments=from_path_strings(output.attachments),
                raw_content=content,
            )
        except Exception:  # noqa: BLE001
            logger.warning("步骤输出非 JSON，按纯文本处理")
            return StepExecutionResult(
                success=True,
                result=content,
                raw_content=content,
            )

    async def _parse_summarize_output(self, content: str) -> SummarizeResult:
        """解析任务汇总 JSON 输出。"""
        try:
            parsed = await self._json_parser.invoke(content)
            output = SummarizeOutput.model_validate(parsed)
            return SummarizeResult(
                message=output.message,
                attachments=from_path_strings(output.attachments),
            )
        except Exception:  # noqa: BLE001
            logger.warning("汇总输出非 JSON，按纯文本处理")
            return SummarizeResult(message=content)

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

    async def _parse_tool_arguments(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        if isinstance(raw, str):
            parsed = await self._json_parser.invoke(raw, default_value={})
            if isinstance(parsed, dict):
                return parsed
            raise ValidationError("invalid tool call arguments")
        raise ValidationError("invalid tool call arguments")

    @staticmethod
    def _extract_ask_user_question(arguments: dict[str, Any]) -> str:
        """从 ``message_ask_user`` 参数中提取问题文本。"""
        for key in ("text", "question", "message", "content"):
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
