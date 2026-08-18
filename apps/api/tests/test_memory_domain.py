"""Memory 领域模型测试。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.memory import MemoryKind, TaskMemoryStore
from domain.task.identifiers import TaskId


def test_task_memory_store_record_and_recall() -> None:
    task_id = TaskId()
    store = TaskMemoryStore.create(task_id)

    store.record(
        kind=MemoryKind.EPISODIC,
        content="用户要求分析竞品 A 与 B",
        agent_role=AgentRole.COORDINATOR,
    )
    store.record(
        kind=MemoryKind.WORKING,
        content="researcher 已找到 3 份公开报告",
        agent_role=AgentRole.RESEARCHER,
    )

    episodic = store.recall(kind=MemoryKind.EPISODIC)
    assert len(episodic) == 1
    assert "竞品" in episodic[0].content

    researcher = store.recall(agent_role=AgentRole.RESEARCHER)
    assert len(researcher) == 1
    assert researcher[0].agent_role is AgentRole.RESEARCHER


def test_task_memory_store_build_context_and_clear_working() -> None:
    store = TaskMemoryStore.create(TaskId())
    store.record(kind=MemoryKind.WORKING, content="临时笔记", agent_role=AgentRole.CODER)
    store.record(kind=MemoryKind.SEMANTIC, content="长期事实：目标市场是北美", agent_role=AgentRole.PLANNER)

    context = store.build_context(limit=5)
    assert "[working]" in context
    assert "[semantic]" in context

    store.clear_working()
    assert store.recall(kind=MemoryKind.WORKING) == []
    assert len(store.recall(kind=MemoryKind.SEMANTIC)) == 1


def test_task_memory_store_promote_to_semantic() -> None:
    store = TaskMemoryStore.create(TaskId())
    entry = store.record(
        kind=MemoryKind.EPISODIC,
        content="关键结论：竞品 B 定价更低",
        agent_role=AgentRole.REVIEWER,
    )
    semantic = store.promote_to_semantic(entry.memory_id)
    assert semantic.kind is MemoryKind.SEMANTIC
    assert "竞品 B" in semantic.content
