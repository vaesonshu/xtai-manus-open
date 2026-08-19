"""基于 Redis Stream 的后台任务执行实例。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import ClassVar

from domain.ports.message_queue import MessageQueuePort
from domain.task.identifiers import TaskId
from domain.task.ports import TaskExecutionPort, TaskRunnerPort
from infrastructure.message_queue.redis_stream_message_queue import (
    RedisStreamMessageQueue,
)

logger = logging.getLogger(__name__)


class RedisStreamTask(TaskExecutionPort):
    """基于 Redis Stream 的任务执行实例，显式实现 ``TaskExecutionPort``。"""

    _task_registry: ClassVar[dict[str, RedisStreamTask]] = {}

    def __init__(self, task_runner: TaskRunnerPort) -> None:
        self._task_runner = task_runner
        self._id = str(uuid.uuid4())
        self._execution_task: asyncio.Task[None] | None = None

        self._input_stream = RedisStreamMessageQueue(f"task:input:{self._id}")
        self._output_stream = RedisStreamMessageQueue(f"task:output:{self._id}")

        RedisStreamTask._task_registry[self._id] = self

    def _cleanup_registry(self) -> None:
        if self._id in RedisStreamTask._task_registry:
            del RedisStreamTask._task_registry[self._id]
            logger.info("任务[%s]已从注册中心移除", self._id)

    def _on_task_done(self) -> None:
        if self._task_runner:
            asyncio.create_task(self._task_runner.on_done(self))
        if hasattr(self._task_runner, "should_keep_execution_alive"):
            if self._task_runner.should_keep_execution_alive(TaskId(self._id)):
                logger.info("任务[%s]等待用户输入，保留执行实例", self._id)
                return
        self._cleanup_registry()

    @classmethod
    def output_stream_for(cls, task_id: str) -> MessageQueuePort:
        """按任务 ID 打开输出流（任务结束后仍可回放 SSE 事件）。"""
        return RedisStreamMessageQueue(f"task:output:{task_id}")

    async def _execute_task(self) -> None:
        try:
            await self._task_runner.invoke(self)
        except asyncio.CancelledError:
            logger.info("任务[%s]执行被取消", self._id)
            raise
        except Exception:  # noqa: BLE001 - 记录后由 finally 统一清理
            logger.exception("任务[%s]执行出现异常", self._id)
        finally:
            self._on_task_done()

    async def invoke(self) -> None:
        """在后台启动任务执行（``done`` 为 True 时可启动）。"""
        if self.done:
            self._execution_task = asyncio.create_task(self._execute_task())
            logger.info("任务[%s]开始执行", self._id)

    def cancel(self) -> bool:
        if not self.done and self._execution_task is not None:
            self._execution_task.cancel()
            logger.info("任务[%s]已取消", self._id)
            self._cleanup_registry()
            return True

        self._cleanup_registry()
        return True

    @property
    def input_stream(self) -> MessageQueuePort:
        return self._input_stream

    @property
    def output_stream(self) -> MessageQueuePort:
        return self._output_stream

    @property
    def task_id(self) -> str:
        return self._id

    @property
    def done(self) -> bool:
        if self._execution_task is None:
            return True
        return self._execution_task.done()

    @classmethod
    def get(cls, task_id: str) -> TaskExecutionPort | None:
        return cls._task_registry.get(task_id)

    @classmethod
    def create(cls, task_runner: TaskRunnerPort) -> TaskExecutionPort:
        return cls(task_runner)

    @classmethod
    async def destroy(cls) -> None:
        for task_id in list(cls._task_registry):
            task = cls._task_registry[task_id]
            task.cancel()
            if task._task_runner:
                await task._task_runner.destroy()
        cls._task_registry.clear()
