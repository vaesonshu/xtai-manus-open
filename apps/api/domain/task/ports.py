"""Task 子域端口：执行与持久化关注点。"""

from __future__ import annotations

from typing import Protocol

from domain.ports.message_queue import MessageQueuePort


class TaskRunnerPort(Protocol):
    """任务运行器端口（执行策略关注点）。

    关心如何执行、销毁与完成回调，不关心规划细节。
    """

    async def invoke(self, task: TaskExecutionPort) -> None:
        """驱动任务执行主循环。"""
        ...

    async def destroy(self) -> None:
        """释放运行器持有的外部资源。"""
        ...

    async def on_done(self, task: TaskExecutionPort) -> None:
        """任务结束后的清理或持久化回调。"""
        ...


class TaskExecutionPort(Protocol):
    """任务执行实例端口（后台任务注册表关注点）。

    封装 invoke/cancel、消息流与任务注册。
    """

    async def invoke(self) -> None:
        """启动后台执行。"""
        ...

    def cancel(self) -> bool:
        """取消任务。"""
        ...

    @property
    def input_stream(self) -> MessageQueuePort:
        """任务输入流。"""
        ...

    @property
    def output_stream(self) -> MessageQueuePort:
        """任务输出流（事件/SSE）。"""
        ...

    @property
    def task_id(self) -> str:
        """任务 ID。"""
        ...

    @property
    def done(self) -> bool:
        """是否已结束（未启动或 asyncio.Task 已完成时为 True）。"""
        ...

    @classmethod
    def get(cls, task_id: str) -> TaskExecutionPort | None:
        """从注册表按 ID 获取任务实例。"""
        ...

    @classmethod
    def create(cls, task_runner: TaskRunnerPort) -> TaskExecutionPort:
        """根据运行器创建任务实例。"""
        ...

    @classmethod
    async def destroy(cls) -> None:
        """销毁所有已注册任务。"""
        ...
