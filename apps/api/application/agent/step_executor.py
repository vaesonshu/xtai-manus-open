"""步骤执行器：将单步规划包装为 ReAct 调用。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from application.agent.prompts import EXECUTION_PROMPT
from application.agent.react_executor import ReActExecutor
from domain.event.base import StreamEvent
from domain.task.identifiers import TaskId
from domain.task.step import TaskStep

OnEventCallback = Callable[[StreamEvent], Awaitable[None]]


class StepExecutor:
    """按步骤描述驱动对应角色的 ReAct 执行器。"""

    def __init__(self, react_executor: ReActExecutor) -> None:
        self._react = react_executor

    async def execute(
        self,
        *,
        task_id: TaskId,
        step: TaskStep,
        on_event: OnEventCallback | None = None,
    ) -> str:
        """执行单个规划步骤并返回文本结果。"""
        query = EXECUTION_PROMPT.format(
            step_description=step.description,
            agent_role=step.agent_role.value,
        )
        return await self._react.invoke(
            task_id=task_id,
            agent_role=step.agent_role,
            query=query,
            on_event=on_event,
        )


class OfflineStepExecutor:
    """离线步骤执行器：不调用 LLM，用于测试与降级。"""

    async def execute(
        self,
        *,
        task_id: TaskId,
        step: TaskStep,
        on_event: OnEventCallback | None = None,
    ) -> str:
        del task_id, on_event
        return f"[{step.agent_role.value}] 已完成：{step.description}"
