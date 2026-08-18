"""AgentTaskRunner 人机协作（WAITING / 恢复）集成测试。"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from application.agent.step_result import StepExecutionResult, SummarizeResult
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.task.agent_task_runner import AgentTaskRunner
from domain.agent.role import AgentRole
from domain.exceptions import WaitForUserInputError
from domain.task import TaskStatus
from domain.task.identifiers import TaskId
from domain.task.step import TaskStep
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from infrastructure.task.redis_stream_task import RedisStreamTask
from tests.test_planning_service import FakeLlmRuntime


class WaitingStepExecutor:
    """模拟步骤执行中需要用户输入的场景。"""

    def __init__(self) -> None:
        self._resume_calls = 0
        self._waited_once = False

    async def execute(
        self,
        *,
        task_id: TaskId,
        step: TaskStep,
        on_event=None,
        context=None,
        resume: bool = False,
    ) -> StepExecutionResult:
        del task_id, on_event, context
        if resume:
            self._resume_calls += 1
            text = f"[{step.agent_role.value}] 用户已回复，步骤完成。"
            return StepExecutionResult(success=True, result=text, raw_content=text)
        if not self._waited_once:
            self._waited_once = True
            raise WaitForUserInputError(
                "等待用户输入",
                agent_role=step.agent_role,
                question="请确认是否继续？",
            )
        text = f"[{step.agent_role.value}] 已完成：{step.description}"
        return StepExecutionResult(success=True, result=text, raw_content=text)

    async def summarize(self, *, task_id: TaskId, goal: str, on_event=None) -> SummarizeResult:
        del task_id, on_event
        return SummarizeResult(message=f"任务「{goal}」已完成。")


@pytest.fixture
def fake_async_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_agent_task_runner_wait_and_resume(fake_async_redis: FakeAsyncRedis) -> None:
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    step_executor = WaitingStepExecutor()
    runner = AgentTaskRunner(
        memory_service=memory_service,
        planning_service=planning_service,
        task_repository=task_repo,
        step_executor=step_executor,
        replan_after_each_step=False,
    )

    task = RedisStreamTask.create(runner)
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
    assert agent_task.status is TaskStatus.WAITING
    assert agent_task.waiting_agent_role is AgentRole.RESEARCHER

    events: list[dict] = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)
    event_types = [item.get("type") for item in events]
    assert "wait" in event_types
    assert "done" not in event_types

    await task.input_stream.put({"content": "确认继续"})
    await task.invoke()

    for _ in range(150):
        if task.done:
            break
        await asyncio.sleep(0.02)

    agent_task = task_repo.get(TaskId(task.task_id))
    assert agent_task is not None
    assert agent_task.status is TaskStatus.COMPLETED
    assert step_executor._resume_calls == 1

    events = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)
    assert any(item.get("type") == "done" for item in events)
