"""规划应用服务测试。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from application.memory.service import MemoryApplicationService
from application.planning.service import PlanningApplicationService
from domain.agent.role import AgentRole
from domain.memory.kind import MemoryKind
from domain.planning.step_spec import PlanStepSpec
from domain.task import AgentTask, TaskPlan
from domain.task.identifiers import TaskId
from infrastructure.memory.in_memory_repository import InMemoryMemoryStoreRepository


class FakeLlmProvider:
    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        del messages, tools, response_format, tool_choice
        payload = {
            "title": "竞品分析规划",
            "message": "按调研-实现-复核执行",
            "steps": [
                {"agent_role": "researcher", "description": "收集公开资料"},
                {"agent_role": "coder", "description": "整理对比表"},
                {"agent_role": "reviewer", "description": "复核结论"},
            ],
        }
        return {"content": json.dumps(payload, ensure_ascii=False)}


class FakeLlmRuntime:
    def get_provider(self) -> FakeLlmProvider:
        return FakeLlmProvider()


@pytest.mark.asyncio
async def test_planning_service_create_plan_with_memory() -> None:
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)

    task_id = TaskId()
    memory_service.record(
        task_id,
        kind=MemoryKind.EPISODIC,
        content="用户关注定价策略",
        agent_role=AgentRole.COORDINATOR,
    )

    plan = await planning_service.create_plan(
        task_id=task_id,
        goal="分析竞品",
        title="竞品分析",
    )

    assert plan.title == "竞品分析"
    assert len(plan.steps) == 3
    assert plan.steps[0].agent_role is AgentRole.RESEARCHER

    memories = memory_service.recall(task_id, kind=MemoryKind.EPISODIC)
    assert any("已生成规划" in item.content for item in memories)


@pytest.mark.asyncio
async def test_planning_service_replan() -> None:
    memory_repo = InMemoryMemoryStoreRepository()
    memory_service = MemoryApplicationService(memory_repo)
    planning_service = PlanningApplicationService(FakeLlmRuntime(), memory_service)

    task = AgentTask.create(goal="分析竞品")
    offline_plan = planning_service.create_plan_offline(
        goal="分析竞品",
        title="初始规划",
        step_specs=[
            PlanStepSpec(description="旧步骤 1", agent_role=AgentRole.EXECUTOR),
            PlanStepSpec(description="旧步骤 2", agent_role=AgentRole.EXECUTOR),
        ],
    )
    task.attach_plan(offline_plan)
    task.start()
    task.begin_next_step()
    task.complete_current_step("完成旧步骤 1")

    added = await planning_service.replan(task, reason="需要增加代码实现步骤")
    assert len(added) == 3
    assert task.plan is not None
    assert task.plan.get_next_step() is added[0]
