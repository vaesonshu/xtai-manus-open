"""流式事件 Presentation Schema 校验测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from domain.event import (
    assistant_message,
    done_event,
    plan_created,
    tool_called,
    user_message,
    wait_event,
)
from domain.file.attachment import FileAttachment
from domain.task.plan import TaskPlan
from presentation.api.stream_event_schemas import validate_stream_event_payload


def test_validate_plan_event_payload() -> None:
    plan = TaskPlan.create(title="t", goal="g")
    payload = plan_created(plan).as_dict()
    validated = validate_stream_event_payload(payload)
    assert validated["type"] == "plan"
    assert validated["status"] == "created"


def test_validate_message_partial_fields() -> None:
    payload = assistant_message("hi", partial=True, stream_id="s-1").as_dict()
    validated = validate_stream_event_payload(payload)
    assert validated["partial"] is True
    assert validated["stream_id"] == "s-1"


def test_validate_wait_event_payload() -> None:
    payload = wait_event(reason="need input", question="请确认").as_dict()
    validated = validate_stream_event_payload(payload)
    assert validated["question"] == "请确认"


def test_validate_tool_event_with_tool_content() -> None:
    payload = tool_called(
        tool_call_id="c1",
        tool_name="file",
        function_name="read_file",
        function_args={"filepath": "a.txt"},
        function_result={"success": True, "message": "hello"},
        tool_content={
            "type": "file",
            "operation": "read",
            "path": "a.txt",
            "content": "hello",
            "success": True,
        },
    ).as_dict()
    validated = validate_stream_event_payload(payload)
    assert validated["tool_content"]["type"] == "file"


def test_validate_message_with_file_attachments() -> None:
    attachment = FileAttachment.from_filepath("/workspace/report.md")
    payload = assistant_message(
        "交付报告",
        attachments=[attachment],
    ).as_dict()
    validated = validate_stream_event_payload(payload)
    assert validated["attachments"][0]["filepath"] == "/workspace/report.md"
    assert validated["attachments"][0]["filename"] == "report.md"


def test_validate_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        validate_stream_event_payload(
            {"id": "1", "type": "unknown", "created_at": "2026-01-01T00:00:00"}
        )


def test_validate_user_message_and_done() -> None:
    assert validate_stream_event_payload(user_message("hi").as_dict())["role"] == "user"
    assert validate_stream_event_payload(done_event().as_dict())["type"] == "done"
