"""工具调用流式事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.event.base import StreamEvent
from domain.event.status import ToolEventStatus


@dataclass
class ToolStreamEvent(StreamEvent):
    """工具调用过程事件（calling / called）。"""

    tool_call_id: str = ""
    tool_name: str = ""
    function_name: str = ""
    function_args: dict[str, Any] = field(default_factory=dict)
    function_result: Any = None
    status: ToolEventStatus = ToolEventStatus.CALLING

    @property
    def type(self) -> str:
        return "tool"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload.update(
            {
                "tool_call_id": self.tool_call_id,
                "tool_name": self.tool_name,
                "function_name": self.function_name,
                "function_args": self.function_args,
                "function_result": self.function_result,
                "status": self.status.value,
            }
        )
        return payload
