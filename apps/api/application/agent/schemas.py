"""ReAct Agent 结构化输出的 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StepExecutionOutput(BaseModel):
    """步骤执行 JSON 输出 schema。"""

    success: bool = True
    result: str = ""
    attachments: list[str] = Field(default_factory=list)


class SummarizeOutput(BaseModel):
    """任务汇总 JSON 输出 schema。"""

    message: str = ""
    attachments: list[str] = Field(default_factory=list)
