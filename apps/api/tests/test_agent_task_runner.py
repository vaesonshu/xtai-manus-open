"""AgentTaskRunner 集成测试。"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.agent.step_executor import OfflineStepExecutor
from application.task.agent_task_runner import AgentTaskRunner
from domain.agent.role import AgentRole
from domain.task import TaskStatus
from domain.task.identifiers import TaskId
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from infrastructure.task.redis_stream_task import RedisStreamTask
from tests.test_planning_service import FakeLlmRuntime


@pytest.fixture
def fake_async_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_agent_task_runner_full_loop(fake_async_redis: FakeAsyncRedis) -> None:
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    runner = AgentTaskRunner(
        memory_service=memory_service,
        planning_service=planning_service,
        task_repository=task_repo,
        step_executor=OfflineStepExecutor(),
        replan_after_each_step=False,
    )

    task = RedisStreamTask.create(runner)
    assert isinstance(task, RedisStreamTask)
    task.input_stream.bind_redis(fake_async_redis)  # type: ignore[attr-defined]
    task.output_stream.bind_redis(fake_async_redis)  # type: ignore[attr-defined]

    await task.input_stream.put({"goal": "分析竞品"})
    await task.invoke()

    for _ in range(100):
        if task.done:
            break
        await asyncio.sleep(0.02)

    agent_task = task_repo.get(TaskId(task.task_id))
    assert agent_task is not None
    assert agent_task.status is TaskStatus.COMPLETED
    assert agent_task.plan is not None
    assert len(agent_task.plan_history) >= 1

    researcher = memory_service.get_agent_conversation(
        TaskId(task.task_id),
        AgentRole.RESEARCHER,
    )
    assert not researcher.empty

    assert await task.output_stream.size() >= 3

    events: list[dict] = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)

    event_types = [item.get("type") for item in events]
    assert "plan" in event_types
    assert "step" in event_types
    assert "done" in event_types
