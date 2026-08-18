"""LangGraphTaskRunner 集成测试。"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from application.agent.step_executor import OfflineStepExecutor
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.task.execution_service import TaskExecutionApplicationService
from application.task.service import TaskApplicationService
from domain.task import TaskStatus
from domain.task.identifiers import TaskId
from infrastructure.config import Settings
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.graph import build_agent_graph
from infrastructure.langgraph.task_runner import LangGraphTaskRunner
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.persistence.checkpointer import get_checkpointer
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from infrastructure.task.in_memory_stream_task import InMemoryStreamTask
from infrastructure.task.task_execution_factory import TaskExecutionFactory
from tests.test_planning_service import FakeLlmRuntime


def _build_langgraph_runner(
    *,
    replan: bool = False,
) -> tuple[LangGraphTaskRunner, InMemoryTaskRepository]:
    settings = Settings(
        agent_use_llm_planning=replan,
        agent_orchestrator="langgraph",
        checkpoint_db_path=":memory:",
    )
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    emitter = GraphEventEmitter()
    node_deps = GraphNodeDependencies(
        planning_service=planning_service,
        memory_service=memory_service,
        step_executor=OfflineStepExecutor(),
        task_repository=task_repo,
        settings=settings,
    )
    checkpointer = get_checkpointer(settings.checkpoint_db_path)
    graph = build_agent_graph(
        settings,
        node_deps=node_deps,
        emitter=emitter,
        checkpointer=checkpointer,
    )
    runner = LangGraphTaskRunner(
        graph=graph,
        memory_service=memory_service,
        task_repository=task_repo,
        event_emitter=emitter,
        checkpointer=checkpointer,
        settings=settings,
    )
    return runner, task_repo


@pytest.mark.asyncio
async def test_langgraph_task_runner_full_loop() -> None:
    runner, task_repo = _build_langgraph_runner()
    task = InMemoryStreamTask.create(runner)

    await task.input_stream.put({"goal": "分析竞品"})
    await task.invoke()

    for _ in range(150):
        if task.done:
            break
        await asyncio.sleep(0.02)

    agent_task = task_repo.get(TaskId(task.task_id))
    assert agent_task is not None
    assert agent_task.status is TaskStatus.COMPLETED
    assert agent_task.plan is not None

    events: list[dict] = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)
    event_types = [item.get("type") for item in events]
    assert "plan" in event_types
    assert "step" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_langgraph_execution_service() -> None:
    runner, task_repo = _build_langgraph_runner()
    task_service = TaskApplicationService(task_repo)
    execution_service = TaskExecutionApplicationService(
        task_runner=runner,
        task_service=task_service,
        execution_factory=TaskExecutionFactory(use_redis=False),
    )

    task_id = await execution_service.start("整理会议纪要")
    for _ in range(150):
        await asyncio.sleep(0.02)
        task = task_repo.get(TaskId(task_id))
        if task is not None and task.status is TaskStatus.COMPLETED:
            break

    assert task is not None
    assert task.status is TaskStatus.COMPLETED
