"""应用层 DTO（数据传输对象）：跨层传输的纯数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent.entity import RunStatus
from domain.primitives import RunId


@dataclass(frozen=True)
class StartAgentRunCommand:
    """发起一次 agent 运行的命令。"""

    goal: str


@dataclass(frozen=True)
class AgentRunDTO:
    """运行结果只读视图（用于查询/响应）。"""

    run_id: str
    goal: str
    status: RunStatus
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def from_entity(cls, run_id: RunId, goal: str, status: RunStatus,
                    result: dict[str, Any], error: str | None) -> AgentRunDTO:
        return cls(
            run_id=str(run_id),
            goal=goal,
            status=status,
            result=result,
            error=error,
        )
