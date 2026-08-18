"""记忆类型：按生命周期与共享范围划分。"""

from __future__ import annotations

from enum import Enum


class MemoryKind(str, Enum):
    """记忆分层模型。

    - WORKING：当前步骤的工作记忆，步骤结束后可被压缩
    - EPISODIC：任务内事件/对话序列
    - SEMANTIC：从 episodic 提炼的可复用事实
    - SHARED：多 Agent 共享黑板，供协作读写
    """

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    SHARED = "shared"
