"""规划 DTO 测试。"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from application.planning.dto import LlmPlanOutput, PlanStepDto
from application.planning.schema import build_plan_response_format
from domain.agent.role import AgentRole


def test_llm_plan_output_parses_valid_json() -> None:
    payload = {
        "title": "竞品分析",
        "message": "按步骤执行",
        "steps": [
            {"agent_role": "researcher", "description": "收集资料"},
            {"agent_role": "coder", "description": "整理报告"},
        ],
    }
    output = LlmPlanOutput.model_validate_json(json.dumps(payload, ensure_ascii=False))
    specs = output.to_step_specs()
    assert len(specs) == 2
    assert specs[0].agent_role is AgentRole.RESEARCHER


def test_llm_plan_output_rejects_invalid_role() -> None:
    payload = {
        "title": "t",
        "message": "",
        "steps": [{"agent_role": "invalid_role", "description": "x"}],
    }
    with pytest.raises(PydanticValidationError):
        LlmPlanOutput.model_validate(payload)


def test_plan_response_format_generated_from_pydantic() -> None:
    response_format = build_plan_response_format()
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert schema["type"] == "object"
    assert "steps" in schema["properties"]
    assert set(schema["required"]) == set(schema["properties"].keys())

    step_schema = schema["$defs"]["PlanStepDto"]
    assert set(step_schema["required"]) == set(step_schema["properties"].keys())

def test_plan_step_dto_to_spec() -> None:
    dto = PlanStepDto(agent_role="reviewer", description="复核")
    assert dto.to_spec().agent_role is AgentRole.REVIEWER
