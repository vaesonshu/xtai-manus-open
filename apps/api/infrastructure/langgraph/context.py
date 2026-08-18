"""LangGraph 运行上下文：在节点与 TaskRunner 之间传递 execution 句柄。"""

from __future__ import annotations

from contextvars import ContextVar

from domain.task.ports import TaskExecutionPort

# 当前图执行绑定的 Task 实例（供节点推送 SSE 事件）
_current_execution: ContextVar[TaskExecutionPort | None] = ContextVar(
    "langgraph_execution",
    default=None,
)


def bind_execution(execution: TaskExecutionPort):
    """绑定 execution，返回 token 供 reset。"""
    return _current_execution.set(execution)


def reset_execution(token: object) -> None:
    """恢复 execution 上下文。"""
    _current_execution.reset(token)  # type: ignore[arg-type]


def get_execution() -> TaskExecutionPort | None:
    """获取当前 execution（节点内发事件用）。"""
    return _current_execution.get()
