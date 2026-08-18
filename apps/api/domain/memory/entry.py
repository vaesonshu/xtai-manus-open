"""记忆条目实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent.role import AgentRole
from domain.exceptions import ValidationError
from domain.memory.identifiers import MemoryId
from domain.memory.kind import MemoryKind
from domain.primitives import Timestamp


@dataclass
class MemoryEntry:
    """单条记忆：记录谁在何时以何种类型写入什么内容。"""

    memory_id: MemoryId
    kind: MemoryKind
    content: str
    agent_role: AgentRole = AgentRole.COORDINATOR
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: Timestamp = field(default_factory=Timestamp)

    @classmethod
    def create(
        cls,
        *,
        kind: MemoryKind,
        content: str,
        agent_role: AgentRole = AgentRole.COORDINATOR,
        metadata: dict[str, Any] | None = None,
        memory_id: MemoryId | None = None,
    ) -> MemoryEntry:
        if not content or not content.strip():
            raise ValidationError("memory content must not be empty")
        return cls(
            memory_id=memory_id or MemoryId(),
            kind=kind,
            content=content.strip(),
            agent_role=agent_role,
            metadata=dict(metadata or {}),
        )
