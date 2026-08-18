"""Agent 执行配置。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentExecutionConfig:
    """ReAct 执行循环的运行参数。"""

    max_retries: int = 3
    max_iterations: int = 10
    retry_interval: float = 1.0
