"""多 Agent 角色定义：规划步骤的执行者身份。"""

from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    """Agent 角色枚举。

    每个规划步骤可绑定一个角色，由对应能力的子 Agent 执行。
    """

    COORDINATOR = "coordinator"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"

    @classmethod
    def from_value(cls, value: str) -> AgentRole:
        """从字符串解析角色，未知值回落为 ``EXECUTOR``。"""
        normalized = (value or "").strip().lower()
        for role in cls:
            if role.value == normalized:
                return role
        return cls.EXECUTOR
