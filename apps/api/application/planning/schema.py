"""多 Agent 规划 LLM 响应格式。"""

from __future__ import annotations

from application.planning.dto import LlmPlanOutput
from application.prompts.planner import (
    CREATE_PLAN_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    REPLANNER_SYSTEM_PROMPT,
    REPLAN_PROMPT,
)

__all__ = [
    "CREATE_PLAN_PROMPT",
    "PLANNER_SYSTEM_PROMPT",
    "PLAN_RESPONSE_FORMAT",
    "REPLANNER_SYSTEM_PROMPT",
    "REPLAN_PROMPT",
    "build_plan_response_format",
]


def build_plan_response_format() -> dict:
    """由 Pydantic 模型生成 OpenAI ``json_schema`` 响应格式。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "multi_agent_plan",
            "strict": True,
            "schema": LlmPlanOutput.model_json_schema(),
        },
    }


# 兼容既有引用
PLAN_RESPONSE_FORMAT: dict = build_plan_response_format()
