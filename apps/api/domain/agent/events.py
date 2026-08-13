"""agent 聚合根相关领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.primitives import DomainEvent


@dataclass
class AgentRunStarted(DomainEvent):
    """一次 agent 运行已创建。"""

    goal: str = ""


@dataclass
class AgentRunProgressed(DomainEvent):
    """agent 运行产生阶段性进展。"""

    step: int = 0
    message: str = ""


@dataclass
class AgentRunCompleted(DomainEvent):
    """agent 运行成功完成。"""

    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunFailed(DomainEvent):
    """agent 运行失败。"""

    error: str = ""
