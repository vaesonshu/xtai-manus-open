"""Task 执行实例工厂：按配置选择 Redis 或内存实现。"""

from __future__ import annotations

from typing import Protocol

from domain.task.ports import TaskExecutionPort, TaskRunnerPort
from infrastructure.task.in_memory_stream_task import InMemoryStreamTask
from infrastructure.task.redis_stream_task import RedisStreamTask


class TaskExecutionBackend(Protocol):
    """Task 执行后端协议（类方法集合）。"""

    @classmethod
    def create(cls, task_runner: TaskRunnerPort) -> TaskExecutionPort: ...

    @classmethod
    def get(cls, task_id: str) -> TaskExecutionPort | None: ...

    @classmethod
    def output_stream_for(cls, task_id: str): ...


class TaskExecutionFactory:
    """根据运行时配置选择 Redis Stream 或内存队列。"""

    def __init__(self, *, use_redis: bool) -> None:
        self._backend: type[TaskExecutionBackend] = (
            RedisStreamTask if use_redis else InMemoryStreamTask  # type: ignore[assignment]
        )

    def create(self, task_runner: TaskRunnerPort) -> TaskExecutionPort:
        return self._backend.create(task_runner)

    def get(self, task_id: str) -> TaskExecutionPort | None:
        return self._backend.get(task_id)

    def output_stream_for(self, task_id: str):
        return self._backend.output_stream_for(task_id)
