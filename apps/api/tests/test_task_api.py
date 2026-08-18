"""Task API 集成测试。"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from application.agent.step_executor import OfflineStepExecutor
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.task.agent_task_runner import AgentTaskRunner
from application.task.execution_service import TaskExecutionApplicationService
from application.task.service import TaskApplicationService
from domain.task import TaskStatus
from domain.task.identifiers import TaskId
from infrastructure import Container, build_container
from infrastructure.config import Settings
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from infrastructure.task.in_memory_stream_task import InMemoryStreamTask
from infrastructure.task.task_execution_factory import TaskExecutionFactory
from main import create_app
from presentation.deps import get_container
from tests.test_planning_service import FakeLlmRuntime


def _build_test_container(*, offline: bool = True) -> Container:
    """构建使用内存队列与可选离线执行器的测试容器。"""
    settings = Settings(
        redis_enabled=False,
        database_enabled=False,
        agent_use_llm_planning=False,
    )
    container = build_container(settings)

    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    step_executor = OfflineStepExecutor() if offline else container.agent_task_runner._step_executor  # noqa: SLF001

    container.memory_repository = memory_repo
    container.memory_service = memory_service
    container.planning_service = planning_service
    container.task_repository = task_repo
    container.task_service = TaskApplicationService(task_repo)
    container.agent_task_runner = AgentTaskRunner(
        memory_service=memory_service,
        planning_service=planning_service,
        task_repository=task_repo,
        step_executor=step_executor,
        replan_after_each_step=False,
    )
    container.task_execution_factory = TaskExecutionFactory(use_redis=False)
    container.task_execution_service = TaskExecutionApplicationService(
        task_runner=container.agent_task_runner,
        task_service=container.task_service,
        execution_factory=container.task_execution_factory,
    )
    return container


@pytest.mark.asyncio
async def test_task_execution_service_offline_loop() -> None:
    """执行服务能驱动完整离线任务循环。"""
    container = _build_test_container(offline=True)
    task_id = await container.task_execution_service.start("分析竞品")

    task = None
    for _ in range(100):
        await asyncio.sleep(0.02)
        try:
            task = container.task_service.get(TaskId(task_id))
        except Exception:  # noqa: BLE001
            continue
        if task.status is TaskStatus.COMPLETED:
            break

    assert task is not None
    assert task.status is TaskStatus.COMPLETED
    assert task.plan is not None
    assert len(task.plan.steps) == 3

    events: list[dict] = []
    output = InMemoryStreamTask.output_stream_for(task_id)
    async for _message_id, payload in output.get_range():
        events.append(payload)
    assert any(item.get("type") == "done" for item in events)


def test_task_api_start_and_get() -> None:
    """HTTP：创建任务并查询状态。"""
    container = _build_test_container(offline=True)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container

    with TestClient(app) as client:
        response = client.post("/v1/tasks", json={"goal": "写一份调研报告"})
        assert response.status_code == 202
        body = response.json()
        task_id = body["task_id"]
        assert task_id

        for _ in range(100):
            get_resp = client.get(f"/v1/tasks/{task_id}")
            assert get_resp.status_code == 200
            if get_resp.json()["status"] == "completed":
                break
            time.sleep(0.02)

        final = client.get(f"/v1/tasks/{task_id}").json()
        assert final["status"] == "completed"
        assert final["plan"] is not None
        assert len(final["plan"]["steps"]) == 3


def test_task_api_sse_stream() -> None:
    """HTTP：SSE 能收到 plan 与 done 事件。"""
    container = _build_test_container(offline=True)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container

    with TestClient(app) as client:
        task_id = client.post("/v1/tasks", json={"goal": "整理会议纪要"}).json()["task_id"]

        with client.stream("GET", f"/v1/tasks/{task_id}/stream") as response:
            assert response.status_code == 200
            buffer = ""
            event_types: set[str] = set()
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    part, buffer = buffer.split("\n\n", 1)
                    if not part.startswith("data: "):
                        continue
                    payload = json.loads(part[6:])
                    event_types.add(payload.get("type", ""))
                    if payload.get("type") == "done":
                        break
                if "done" in event_types:
                    break

        assert "plan" in event_types
        assert "done" in event_types
