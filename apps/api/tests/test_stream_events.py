"""流式事件模型测试。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.event import (
    assistant_message,
    done_event,
    plan_created,
    step_completed,
    step_started,
    tool_called,
    tool_calling,
    user_message,
)
from domain.event.status import PlanEventStatus, StepEventStatus, ToolEventStatus
from domain.task.plan import TaskPlan


def test_plan_stream_event_serialization() -> None:
    plan = TaskPlan.create(title="调研", goal="分析竞品")
    plan.add_step("收集资料", agent_role=AgentRole.RESEARCHER)

    payload = plan_created(plan).as_dict()
    assert payload["type"] == "plan"
    assert payload["status"] == PlanEventStatus.CREATED.value
    assert payload["plan"]["title"] == "调研"
    assert len(payload["plan"]["steps"]) == 1


def test_step_stream_event_serialization() -> None:
    plan = TaskPlan.create(title="t", goal="g")
    step = plan.add_step("写代码", agent_role=AgentRole.CODER)
    step.start()

    started = step_started(step).as_dict()
    assert started["type"] == "step"
    assert started["status"] == StepEventStatus.STARTED.value

    step.complete("ok")
    completed = step_completed(step).as_dict()
    assert completed["status"] == StepEventStatus.COMPLETED.value


def test_message_and_tool_events() -> None:
    message = user_message("hello").as_dict()
    assert message["type"] == "message"
    assert message["role"] == "user"

    calling = tool_calling(
        tool_call_id="c1",
        tool_name="browser",
        function_name="browser_view",
        function_args={"url": "https://example.com"},
    ).as_dict()
    assert calling["status"] == ToolEventStatus.CALLING.value

    called = tool_called(
        tool_call_id="c1",
        tool_name="browser",
        function_name="browser_view",
        function_args={"url": "https://example.com"},
        function_result={"title": "Example"},
    ).as_dict()
    assert called["status"] == ToolEventStatus.CALLED.value

    assert done_event().as_dict()["type"] == "done"


def test_assistant_message_partial_serialization() -> None:
    payload = assistant_message(
        "生成中…",
        partial=True,
        stream_id="stream-1",
    ).as_dict()
    assert payload["partial"] is True
    assert payload["stream_id"] == "stream-1"
    assert payload["role"] == "assistant"
