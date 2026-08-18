"""记忆应用服务：编排任务级记忆的读写。"""

from __future__ import annotations

from typing import Any

from domain.agent.role import AgentRole
from domain.memory.conversation import ConversationMemory
from domain.memory.entry import MemoryEntry
from domain.memory.kind import MemoryKind
from domain.memory.store import TaskMemoryStore
from domain.ports.memory import MemoryStoreRepository
from domain.task.identifiers import TaskId


class MemoryApplicationService:
    """记忆用例服务：为 Planner / Executor 提供统一读写入口。"""

    def __init__(self, repository: MemoryStoreRepository) -> None:
        self._repository = repository

    def get_store(self, task_id: TaskId) -> TaskMemoryStore:
        return self._repository.get_or_create(task_id)

    def record(
        self,
        task_id: TaskId,
        *,
        kind: MemoryKind,
        content: str,
        agent_role: AgentRole = AgentRole.COORDINATOR,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        store = self.get_store(task_id)
        entry = store.record(
            kind=kind,
            content=content,
            agent_role=agent_role,
            metadata=metadata,
        )
        self._repository.save(store)
        return entry

    def recall(
        self,
        task_id: TaskId,
        *,
        kind: MemoryKind | None = None,
        agent_role: AgentRole | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        store = self.get_store(task_id)
        return store.recall(kind=kind, agent_role=agent_role, limit=limit)

    def build_context(
        self,
        task_id: TaskId,
        *,
        kinds: tuple[MemoryKind, ...] | None = None,
        agent_role: AgentRole | None = None,
        limit: int = 10,
    ) -> str:
        store = self.get_store(task_id)
        structured = store.build_context(kinds=kinds, agent_role=agent_role, limit=limit)
        if agent_role is not None:
            conversation = store.build_agent_messages_context(agent_role, limit=limit)
            if conversation:
                return f"{structured}\n\n{conversation}".strip()
        return structured

    def clear_working(self, task_id: TaskId) -> None:
        store = self.get_store(task_id)
        store.clear_working()
        self._repository.save(store)

    def add_agent_message(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        message: dict[str, Any],
    ) -> None:
        """向指定 Agent 的对话记忆写入消息。"""
        store = self.get_store(task_id)
        store.add_agent_message(agent_role, message)
        self._repository.save(store)

    def get_agent_conversation(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
    ) -> ConversationMemory:
        return self.get_store(task_id).get_agent_conversation(agent_role)

    def compact_conversations(self, task_id: TaskId) -> None:
        """压缩所有 Agent 对话记忆。"""
        store = self.get_store(task_id)
        store.compact_conversations()
        self._repository.save(store)

    def rollback_agent_message(self, task_id: TaskId, agent_role: AgentRole) -> None:
        """回滚指定 Agent 的最后一条对话消息。"""
        store = self.get_store(task_id)
        store.rollback_agent_message(agent_role)
        self._repository.save(store)

    def rollback_for_user_input(
        self,
        task_id: TaskId,
        agent_role: AgentRole,
        user_content: str,
    ) -> None:
        """用户续聊时执行智能回滚（``message_ask_user`` 补 tool，否则删最后一条）。"""
        store = self.get_store(task_id)
        store.rollback_for_user_input(agent_role, user_content)
        self._repository.save(store)
