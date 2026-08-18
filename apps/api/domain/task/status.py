"""Task 子域状态枚举：按关注点拆分生命周期与执行状态。"""

from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    """任务生命周期状态（聚合根级）。

    描述一次 Agent 任务从创建到结束的宏观状态，包含等待用户输入等交互态。
    """

    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """规划/步骤执行状态（规划子域级）。

    仅描述 Plan 与 Step 的执行进度，不与 Task 生命周期混用。
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
