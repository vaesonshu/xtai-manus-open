"""LangGraph 节点依赖注入。"""

from __future__ import annotations

from dataclasses import dataclass

from application.agent.step_executor import OfflineStepExecutor, StepExecutor
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from domain.ports.task import TaskRepository
from infrastructure.config import Settings

StepExecutorLike = StepExecutor | OfflineStepExecutor


@dataclass(frozen=True)
class GraphNodeDependencies:
    """节点可访问的应用层服务（由基础设施层闭包注入）。"""

    planning_service: PlanningApplicationService
    memory_service: MemoryApplicationService
    step_executor: StepExecutorLike
    task_repository: TaskRepository
    settings: Settings
