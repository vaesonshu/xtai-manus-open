"""Task 执行应用服务：HTTP 层与后台 Runner 的桥接。"""

from __future__ import annotations

import logging
from typing import Protocol

from application.task.service import TaskApplicationService
from domain.exceptions import ConflictError, NotFoundError
from domain.ports.message_queue import MessageQueuePort
from domain.task.identifiers import TaskId
from domain.task.ports import TaskExecutionPort, TaskRunnerPort
from domain.task.status import TaskStatus

logger = logging.getLogger(__name__)


class TaskExecutionFactory(Protocol):
    """创建后台 Task 执行实例的工厂。"""

    def create(self, task_runner: TaskRunnerPort) -> TaskExecutionPort:
        ...

    def get(self, task_id: str) -> TaskExecutionPort | None:
        ...

    def output_stream_for(self, task_id: str) -> MessageQueuePort:
        ...


class TaskExecutionApplicationService:
    """编排 Task 的创建、恢复与事件流访问。"""

    def __init__(
        self,
        *,
        task_runner: TaskRunnerPort,
        task_service: TaskApplicationService,
        execution_factory: TaskExecutionFactory,
    ) -> None:
        self._runner = task_runner
        self._tasks = task_service
        self._executions = execution_factory

    async def start(self, goal: str) -> str:
        """创建任务并在后台启动执行，返回 task_id。"""
        execution = self._executions.create(self._runner)
        await execution.input_stream.put({"goal": goal})
        await execution.invoke()
        logger.info("任务[%s]已提交执行", execution.task_id)
        return execution.task_id

    async def reply(self, task_id: str, content: str) -> None:
        """用户在 WAITING 状态下回复并继续执行。"""
        task = self._tasks.get(TaskId(task_id))
        if task.status is not TaskStatus.WAITING:
            raise ConflictError(
                f"task {task_id} is not waiting for user input (status={task.status.value})"
            )

        execution = self._executions.get(task_id)
        if execution is None:
            raise NotFoundError(f"task execution {task_id} not found")

        await execution.input_stream.put({"content": content})
        await execution.invoke()
        logger.info("任务[%s]收到用户回复并继续执行", task_id)

    def get_execution(self, task_id: str) -> TaskExecutionPort | None:
        """获取仍在注册表中的执行实例。"""
        return self._executions.get(task_id)

    def output_stream_for(self, task_id: str) -> MessageQueuePort:
        """获取任务输出事件流（支持已完成任务回放）。"""
        return self._executions.output_stream_for(task_id)
