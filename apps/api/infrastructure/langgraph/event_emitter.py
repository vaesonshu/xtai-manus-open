"""LangGraph 执行过程中的 SSE 事件桥接。"""

from __future__ import annotations

from domain.event.base import StreamEvent
from domain.task.ports import TaskExecutionPort
from infrastructure.langgraph.context import get_execution


class GraphEventEmitter:
    """将领域 ``StreamEvent`` 写入任务 output_stream。"""

    async def emit(self, event: StreamEvent) -> None:
        """推送单条事件到当前 execution。"""
        execution = get_execution()
        if execution is None:
            return
        await execution.output_stream.put(event.as_dict())

    async def emit_to(
        self,
        execution: TaskExecutionPort,
        event: StreamEvent,
    ) -> None:
        """显式指定 execution 推送事件。"""
        await execution.output_stream.put(event.as_dict())
