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


def _ensure_strict_required(schema: dict) -> dict:
    """OpenAI strict json_schema 要求 object 的 required 包含全部 properties。"""
    if schema.get("type") == "object" and "properties" in schema:
        schema["required"] = list(schema["properties"].keys())
        schema["additionalProperties"] = False

    for def_schema in schema.get("$defs", {}).values():
        _ensure_strict_required(def_schema)

    items = schema.get("items")
    if isinstance(items, dict):
        _ensure_strict_required(items)

    return schema


def build_plan_response_format() -> dict:
    """由 Pydantic 模型生成 OpenAI ``json_schema`` 响应格式。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "multi_agent_plan",
            "strict": True,
            "schema": _ensure_strict_required(LlmPlanOutput.model_json_schema()),
        },
    }


# 兼容既有引用
PLAN_RESPONSE_FORMAT: dict = build_plan_response_format()
