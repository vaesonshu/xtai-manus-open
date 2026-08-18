"""对话记忆与规划版本链测试。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.memory import TaskMemoryStore
from domain.memory.conversation import ConversationMemory
from domain.planning import PlanStepSpec
from domain.task import AgentTask, TaskPlan
from domain.task.identifiers import TaskId
from domain.task.plan_snapshot import PlanSnapshot


def test_conversation_memory_compact_and_rollback() -> None:
    memory = ConversationMemory()
    memory.add_message({"role": "user", "content": "hello"})
    memory.add_message(
        {
            "role": "tool",
            "function_name": "browser_view",
            "content": "very long page content" * 100,
        }
    )
    memory.compact()
    assert memory.get_last_message()["content"] == "(removed)"

    memory.roll_back()
    assert memory.get_last_message()["content"] == "hello"


def test_task_memory_store_per_agent_conversations() -> None:
    store = TaskMemoryStore.create(TaskId())
    store.add_agent_message(AgentRole.RESEARCHER, {"role": "user", "content": "调研"})
    store.add_agent_message(AgentRole.CODER, {"role": "user", "content": "写代码"})

    researcher = store.get_agent_conversation(AgentRole.RESEARCHER)
    coder = store.get_agent_conversation(AgentRole.CODER)
    assert len(researcher.get_messages()) == 1
    assert len(coder.get_messages()) == 1
    assert researcher.get_messages()[0]["content"] == "调研"


def test_plan_snapshot_version_chain() -> None:
    task = AgentTask.create(goal="分析竞品")
    plan = TaskPlan.create(title="初始", goal="分析竞品")
    plan.add_step("步骤 1", agent_role=AgentRole.RESEARCHER)
    task.attach_plan(plan)

    assert len(task.plan_history) == 1
    assert task.plan_history[0].version == 1
    assert task.plan_history[0].reason == "initial"

    task.replan(
        [PlanStepSpec(description="新步骤", agent_role=AgentRole.CODER)],
        reason="需求变更",
    )
    assert len(task.plan_history) == 2
    assert task.get_latest_plan_snapshot() is not None
    assert task.get_latest_plan_snapshot().reason == "需求变更"


def test_plan_snapshot_from_plan() -> None:
    plan = TaskPlan.create(title="t", goal="g")
    plan.add_step("s1", agent_role=AgentRole.REVIEWER)
    snapshot = PlanSnapshot.from_plan(plan, version=1, reason="test")
    assert snapshot.steps[0]["agent_role"] == "reviewer"
