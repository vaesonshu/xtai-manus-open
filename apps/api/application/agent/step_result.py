"""步骤执行与汇总结果 DTO。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepExecutionResult:
    """单步 ReAct 执行的结构化输出（对齐参考项目 Step JSON）。"""

    success: bool
    result: str
    attachments: tuple[str, ...] = field(default_factory=tuple)
    raw_content: str = ""

    @property
    def display_text(self) -> str:
        """用于记忆与事件展示的文本。"""
        return self.result or self.raw_content


@dataclass(frozen=True)
class SummarizeResult:
    """任务结束汇总输出。"""

    message: str
    attachments: tuple[str, ...] = field(default_factory=tuple)
