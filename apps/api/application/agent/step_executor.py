"""步骤执行器：将单步规划包装为 ReAct 调用。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from application.prompts.react import EXECUTION_PROMPT
from application.agent.react_executor import ReActExecutor
from application.agent.step_result import StepExecutionResult, SummarizeResult
from domain.event.base import StreamEvent
from domain.task.identifiers import TaskId
from domain.task.step import TaskStep

OnEventCallback = Callable[[StreamEvent], Awaitable[None]]


@dataclass(frozen=True)
class StepExecutionContext:
    """步骤执行上下文，携带 message、attachments、language 等用户侧信息。"""

    message: str = ""
    attachments: str = ""
    language: str = "zh-CN"


class StepExecutor:
    """按步骤描述驱动对应角色的 ReAct 执行器。"""

    def __init__(self, react_executor: ReActExecutor) -> None:
        self._react = react_executor

    async def execute(
        self,
        *,
        task_id: TaskId,
        step: TaskStep,
        context: StepExecutionContext | None = None,
        on_event: OnEventCallback | None = None,
        resume: bool = False,
    ) -> StepExecutionResult:
        """执行单个规划步骤并返回结构化结果。"""
        if resume:
            return await self._react.continue_after_user_input(
                task_id=task_id,
                agent_role=step.agent_role,
                on_event=on_event,
            )

        ctx = context or StepExecutionContext()
        query = EXECUTION_PROMPT.format(
            step=step.description,
            message=ctx.message,
            attachments=ctx.attachments or "(无)",
            language=ctx.language,
        )
        return await self._react.invoke(
            task_id=task_id,
            agent_role=step.agent_role,
            query=query,
            on_event=on_event,
        )

    async def summarize(
        self,
        *,
        task_id: TaskId,
        goal: str,
        on_event: OnEventCallback | None = None,
        deliverables: str = "",
    ) -> SummarizeResult:
        """任务完成后生成汇总交付。"""
        return await self._react.summarize(
            task_id=task_id,
            goal=goal,
            on_event=on_event,
            deliverables=deliverables,
        )


class OfflineStepExecutor:
    """离线步骤执行器：不调用 LLM，用于测试与降级。"""

    async def execute(
        self,
        *,
        task_id: TaskId,
        step: TaskStep,
        context: StepExecutionContext | None = None,
        on_event: OnEventCallback | None = None,
        resume: bool = False,
    ) -> StepExecutionResult:
        del task_id, context, on_event, resume
        text = f"[{step.agent_role.value}] 已完成：{step.description}"
        return StepExecutionResult(success=True, result=text, raw_content=text)

    async def summarize(
        self,
        *,
        task_id: TaskId,
        goal: str,
        on_event: OnEventCallback | None = None,
        deliverables: str = "",
    ) -> SummarizeResult:
        del task_id, on_event, deliverables
        return SummarizeResult(message=f"任务「{goal}」已完成（离线模式）。")
