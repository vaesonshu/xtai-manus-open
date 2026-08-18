"""流式事件基类：供 SSE / Redis Stream 推送给前端。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from domain.primitives import Timestamp


@dataclass
class StreamEvent:
    """流式事件基类（与领域事件 ``TaskDomainEvent`` 分离）。"""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: Timestamp = field(default_factory=Timestamp)

    @property
    def type(self) -> str:
        raise NotImplementedError

    def as_dict(self) -> dict[str, Any]:
        """序列化为可写入消息队列的字典。"""
        return {
            "id": self.event_id,
            "type": self.type,
            "created_at": self.occurred_at.isoformat(),
        }
