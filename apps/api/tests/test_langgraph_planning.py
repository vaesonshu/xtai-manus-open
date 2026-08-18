"""LangGraph 规划桥接与节点冒烟测试。"""

from __future__ import annotations

import pytest

from application.agent.step_executor import OfflineStepExecutor
from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from domain.task.identifiers import TaskId
from domain.task.task import AgentTask
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.execute import make_begin_step_node, make_execute_step_node
from infrastructure.langgraph.nodes.plan import make_plan_node
from infrastructure.langgraph.planning_bridge import build_offline_plan, plan_to_state_steps
from infrastructure.config import Settings
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository
from infrastructure.persistence.in_memory_task_repository import InMemoryTaskRepository
from tests.test_planning_service import FakeLlmRuntime


@pytest.fixture
def node_deps() -> GraphNodeDependencies:
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)
    task_repo = InMemoryTaskRepository()
    settings = Settings(agent_use_llm_planning=False, checkpoint_db_path=":memory:")
    return GraphNodeDependencies(
        planning_service=planning_service,
        memory_service=memory_service,
        step_executor=OfflineStepExecutor(),
        task_repository=task_repo,
        settings=settings,
    )


def test_plan_to_state_steps() -> None:
    plan = build_offline_plan("写一份市场报告")
    steps = plan_to_state_steps(plan)
    assert len(steps) == 3
    assert steps[0]["agent_role"] == "researcher"


@pytest.mark.asyncio
async def test_plan_node_creates_task_plan(node_deps: GraphNodeDependencies) -> None:
    emitter = GraphEventEmitter()
    task_id = TaskId()
    task_repo = node_deps.task_repository
    task_repo.save(AgentTask.create(goal="分析竞品", task_id=task_id))

    plan_node = make_plan_node(node_deps, emitter)
    result = await plan_node(
        {
            "task_id": str(task_id),
            "goal": "分析竞品",
            "use_llm_planning": False,
        }
    )

    assert len(result["plan_steps"]) == 3
    agent_task = task_repo.get(task_id)
    assert agent_task is not None
    assert agent_task.plan is not None


@pytest.mark.asyncio
async def test_execute_step_offline(node_deps: GraphNodeDependencies) -> None:
    emitter = GraphEventEmitter()
    task_id = TaskId()
    task_repo = node_deps.task_repository
    agent_task = AgentTask.create(goal="分析竞品", task_id=task_id)
    plan = build_offline_plan("分析竞品")
    agent_task.attach_plan(plan)
    agent_task.start()
    task_repo.save(agent_task)

    execute_node = make_execute_step_node(node_deps, emitter)
    result = await execute_node(
        {
            "task_id": str(task_id),
            "goal": "分析竞品",
            "resume_step": False,
        }
    )
    assert result.get("last_step_result") is None
    assert result.get("error") == "无运行中的步骤可执行"

    begin_node = make_begin_step_node(node_deps, emitter)
    await begin_node({"task_id": str(task_id), "goal": "分析竞品", "current_step_index": 0})
    result = await execute_node(
        {
            "task_id": str(task_id),
            "goal": "分析竞品",
            "resume_step": False,
        }
    )
    assert result.get("last_step_result") is not None
