"""Task 应用服务：创建与查询 Agent 任务。"""

from __future__ import annotations

from domain.exceptions import NotFoundError
from domain.ports.task import TaskRepository
from domain.task.identifiers import TaskId
from domain.task.task import AgentTask


class TaskApplicationService:
    """任务用例服务（薄编排层）。"""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def get(self, task_id: TaskId) -> AgentTask:
        task = self._repository.get(task_id)
        if task is None:
            raise NotFoundError(f"task {task_id} not found")
        return task

    def save(self, task: AgentTask) -> None:
        self._repository.save(task)
