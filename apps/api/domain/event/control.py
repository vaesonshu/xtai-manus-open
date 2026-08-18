"""消息与控制类流式事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from domain.event.base import StreamEvent


@dataclass
class MessageStreamEvent(StreamEvent):
    """用户/助手消息事件。"""

    role: Literal["user", "assistant"] = "assistant"
    message: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "message"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload.update(
            {
                "role": self.role,
                "message": self.message,
                "attachments": self.attachments,
            }
        )
        return payload


@dataclass
class TitleStreamEvent(StreamEvent):
    """会话标题事件。"""

    title: str = ""

    @property
    def type(self) -> str:
        return "title"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload["title"] = self.title
        return payload


@dataclass
class WaitStreamEvent(StreamEvent):
    """等待用户输入事件。"""

    reason: str = ""
    question: str = ""

    @property
    def type(self) -> str:
        return "wait"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload["reason"] = self.reason
        payload["question"] = self.question
        return payload


@dataclass
class ErrorStreamEvent(StreamEvent):
    """错误事件。"""

    error: str = ""

    @property
    def type(self) -> str:
        return "error"

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload["error"] = self.error
        return payload


@dataclass
class DoneStreamEvent(StreamEvent):
    """任务结束事件。"""

    @property
    def type(self) -> str:
        return "done"
