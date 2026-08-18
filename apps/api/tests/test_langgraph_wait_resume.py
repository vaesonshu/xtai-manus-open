"""LangGraph WAITING / reply 续跑测试。"""

from __future__ import annotations

import asyncio

import pytest

from application.agent.step_result import StepExecutionResult, SummarizeResult
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from application.task.execution_service import TaskExecutionApplicationService
from application.task.service import TaskApplicationService
from domain.agent.role import AgentRole
from domain.exceptions import WaitForUserInputError
from domain.task import TaskStatus
from domain.task.identifiers import TaskId
from domain.task.step import TaskStep
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


class WaitingStepExecutor:
    """模拟步骤执行中需要用户输入。"""

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


def _build_waiting_runner() -> tuple[LangGraphTaskRunner, InMemoryTaskRepository]:
    settings = Settings(
        agent_use_llm_planning=False,
        agent_orchestrator="langgraph",
        checkpoint_db_path=":memory:",
    )
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    step_executor = WaitingStepExecutor()
    emitter = GraphEventEmitter()
    node_deps = GraphNodeDependencies(
        planning_service=planning_service,
        memory_service=memory_service,
        step_executor=step_executor,
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
async def test_langgraph_wait_and_resume() -> None:
    runner, task_repo = _build_waiting_runner()
    task = InMemoryStreamTask.create(runner)
    await task.input_stream.put({"goal": "分析竞品"})
    await task.invoke()

    for _ in range(150):
        if task.done:
            break
        await asyncio.sleep(0.02)

    agent_task = task_repo.get(TaskId(task.task_id))
    assert agent_task is not None
    assert agent_task.status is TaskStatus.WAITING

    events: list[dict] = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)
    assert any(item.get("type") == "wait" for item in events)
    assert not any(item.get("type") == "done" for item in events)

    await task.input_stream.put({"content": "确认继续"})
    await task.invoke()

    for _ in range(200):
        if task.done:
            break
        await asyncio.sleep(0.02)

    agent_task = task_repo.get(TaskId(task.task_id))
    assert agent_task is not None
    assert agent_task.status is TaskStatus.COMPLETED

    events = []
    async for _message_id, payload in task.output_stream.get_range():
        events.append(payload)
    assert any(item.get("type") == "done" for item in events)


@pytest.mark.asyncio
async def test_langgraph_reply_via_execution_service() -> None:
    runner, task_repo = _build_waiting_runner()
    task_service = TaskApplicationService(task_repo)
    execution_service = TaskExecutionApplicationService(
        task_runner=runner,
        task_service=task_service,
        execution_factory=TaskExecutionFactory(use_redis=False),
    )

    task_id = await execution_service.start("分析竞品")
    for _ in range(150):
        await asyncio.sleep(0.02)
        task = task_repo.get(TaskId(task_id))
        if task is not None and task.status is TaskStatus.WAITING:
            break

    assert task is not None
    await execution_service.reply(task_id, "确认继续")

    for _ in range(200):
        await asyncio.sleep(0.02)
        task = task_repo.get(TaskId(task_id))
        if task is not None and task.status is TaskStatus.COMPLETED:
            break

    assert task is not None
    assert task.status is TaskStatus.COMPLETED
