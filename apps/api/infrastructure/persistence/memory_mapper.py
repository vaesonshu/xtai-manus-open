"""TaskMemoryStore 序列化映射（基础设施层 ↔ 领域层）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from domain.agent.role import AgentRole
from domain.memory.conversation import ConversationMemory
from domain.memory.entry import MemoryEntry
from domain.memory.identifiers import MemoryId
from domain.memory.kind import MemoryKind
from domain.memory.store import TaskMemoryStore
from domain.primitives import Timestamp
from domain.task.identifiers import TaskId


def memory_store_to_dict(store: TaskMemoryStore) -> dict[str, Any]:
    """将 ``TaskMemoryStore`` 序列化为可 JSON 存储的字典。"""
    return {
        "task_id": str(store.task_id),
        "entries": [_entry_to_dict(entry) for entry in store.entries],
        "agent_conversations": {
            role: conversation.get_messages()
            for role, conversation in store.agent_conversations.items()
        },
    }


def memory_store_from_dict(payload: dict[str, Any]) -> TaskMemoryStore:
    """从持久化字典还原 ``TaskMemoryStore``。"""
    task_id = TaskId(payload["task_id"])
    store = TaskMemoryStore(task_id=task_id)
    store.entries = [_entry_from_dict(item) for item in payload.get("entries", [])]

    conversations: dict[str, ConversationMemory] = {}
    for role, messages in (payload.get("agent_conversations") or {}).items():
        conversation = ConversationMemory()
        conversation.add_messages(list(messages))
        conversations[role] = conversation
    store.agent_conversations = conversations
    return store


def _entry_to_dict(entry: MemoryEntry) -> dict[str, Any]:
    return {
        "memory_id": str(entry.memory_id),
        "kind": entry.kind.value,
        "content": entry.content,
        "agent_role": entry.agent_role.value,
        "metadata": dict(entry.metadata),
        "created_at": entry.created_at.isoformat(),
    }


def _entry_from_dict(payload: dict[str, Any]) -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(payload["memory_id"]),
        kind=MemoryKind(payload["kind"]),
        content=payload["content"],
        agent_role=AgentRole(payload["agent_role"]),
        metadata=dict(payload.get("metadata") or {}),
        created_at=Timestamp(datetime.fromisoformat(payload["created_at"])),
    )
