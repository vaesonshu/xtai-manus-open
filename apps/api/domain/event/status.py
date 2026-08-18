"""流式事件状态枚举。"""

from __future__ import annotations

from enum import Enum


class PlanEventStatus(str, Enum):
    """规划流式事件状态。"""

    CREATED = "created"
    UPDATED = "updated"
    COMPLETED = "completed"


class StepEventStatus(str, Enum):
    """步骤流式事件状态。"""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolEventStatus(str, Enum):
    """工具流式事件状态。"""

    CALLING = "calling"
    CALLED = "called"
