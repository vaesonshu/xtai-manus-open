"""任务级记忆聚合根：管理多 Agent 协作下的读写与上下文构建。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from typing import Any

from domain.agent.role import AgentRole
from domain.exceptions import NotFoundError, ValidationError
from domain.memory.conversation import ConversationMemory
from domain.memory.entry import MemoryEntry
from domain.memory.identifiers import MemoryId
from domain.memory.kind import MemoryKind
from domain.task.identifiers import TaskId


@dataclass
class TaskMemoryStore:
    """按任务隔离的记忆存储聚合根。"""

    task_id: TaskId
    entries: list[MemoryEntry] = field(default_factory=list)
    # 按 Agent 角色隔离的对话记忆（planner / researcher / coder 等）
    agent_conversations: dict[str, ConversationMemory] = field(default_factory=dict)

    @classmethod
    def create(cls, task_id: TaskId) -> TaskMemoryStore:
        return cls(task_id=task_id)

    def record(
        self,
        *,
        kind: MemoryKind,
        content: str,
        agent_role: AgentRole = AgentRole.COORDINATOR,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """写入一条记忆。"""
        entry = MemoryEntry.create(
            kind=kind,
            content=content,
            agent_role=agent_role,
            metadata=metadata,
        )
        self.entries.append(entry)
        return entry

    def recall(
        self,
        *,
        kind: MemoryKind | None = None,
        agent_role: AgentRole | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """按类型/角色过滤并返回最近条目（时间正序）。"""
        if limit <= 0:
            raise ValidationError("recall limit must be positive")

        filtered = self.entries
        if kind is not None:
            filtered = [item for item in filtered if item.kind is kind]
        if agent_role is not None:
            filtered = [item for item in filtered if item.agent_role is agent_role]

        return filtered[-limit:]

    def build_context(
        self,
        *,
        kinds: tuple[MemoryKind, ...] | None = None,
        agent_role: AgentRole | None = None,
        limit: int = 10,
    ) -> str:
        """拼装供 LLM 使用的记忆上下文字符串。"""
        selected_kinds = kinds or (
            MemoryKind.WORKING,
            MemoryKind.EPISODIC,
            MemoryKind.SEMANTIC,
            MemoryKind.SHARED,
        )
        lines: list[str] = []
        for memory_kind in selected_kinds:
            items = self.recall(kind=memory_kind, agent_role=agent_role, limit=limit)
            if not items:
                continue
            lines.append(f"[{memory_kind.value}]")
            for item in items:
                role = item.agent_role.value
                lines.append(f"- ({role}) {item.content}")
        return "\n".join(lines)

    def clear_working(self) -> None:
        """清空工作记忆（步骤切换时常用）。"""
        self.entries = [
            item for item in self.entries if item.kind is not MemoryKind.WORKING
        ]

    def promote_to_semantic(self, memory_id: MemoryId) -> MemoryEntry:
        """将指定条目提升为语义记忆（长期保留）。"""
        entry = self._get_entry(memory_id)
        semantic = MemoryEntry.create(
            kind=MemoryKind.SEMANTIC,
            content=entry.content,
            agent_role=entry.agent_role,
            metadata={"source_memory_id": str(entry.memory_id)},
        )
        self.entries.append(semantic)
        return semantic

    def get_agent_conversation(self, agent_role: AgentRole) -> ConversationMemory:
        """获取（或懒创建）指定 Agent 的对话记忆。"""
        key = agent_role.value
        if key not in self.agent_conversations:
            self.agent_conversations[key] = ConversationMemory()
        return self.agent_conversations[key]

    def add_agent_message(self, agent_role: AgentRole, message: dict[str, Any]) -> None:
        """向指定 Agent 的对话记忆追加消息。"""
        self.get_agent_conversation(agent_role).add_message(message)

    def compact_conversations(self) -> None:
        """压缩所有 Agent 的对话记忆。"""
        for conversation in self.agent_conversations.values():
            conversation.compact()

    def rollback_agent_message(self, agent_role: AgentRole) -> None:
        """回滚指定 Agent 的最后一条对话消息。"""
        self.get_agent_conversation(agent_role).roll_back()

    def build_agent_messages_context(
        self,
        agent_role: AgentRole,
        *,
        limit: int = 10,
    ) -> str:
        """将 Agent 对话记忆格式化为 LLM 上下文。"""
        messages = self.get_agent_conversation(agent_role).get_messages()[-limit:]
        if not messages:
            return ""
        lines = [f"[{agent_role.value} conversation]"]
        for item in messages:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            lines.append(f"- {role}: {content}")
        return "\n".join(lines)

    def _get_entry(self, memory_id: MemoryId) -> MemoryEntry:
        for entry in self.entries:
            if entry.memory_id.value == memory_id.value:
                return entry
        raise NotFoundError(f"memory entry {memory_id} not found")
