"""规划流式事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.event.base import StreamEvent
from domain.event.status import PlanEventStatus


@dataclass
class PlanStreamEvent(StreamEvent):
    """规划创建/更新/完成事件。"""

    plan: dict[str, Any] = field(default_factory=dict)
    status: PlanEventStatus = PlanEventStatus.CREATED

    @property
    def type(self) -> str:
        return "plan"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload.update({"plan": self.plan, "status": self.status.value})
        return payload
