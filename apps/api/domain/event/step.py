"""步骤流式事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.event.base import StreamEvent
from domain.event.status import StepEventStatus


@dataclass
class StepStreamEvent(StreamEvent):
    """步骤开始/完成/失败事件。"""

    step: dict[str, Any] = field(default_factory=dict)
    status: StepEventStatus = StepEventStatus.STARTED

    @property
    def type(self) -> str:
        return "step"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload.update({"step": self.step, "status": self.status.value})
        return payload
