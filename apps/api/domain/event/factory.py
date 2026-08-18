"""流式事件工厂：将领域对象转换为推送事件。"""

from __future__ import annotations

from typing import Any

from domain.event.control import DoneStreamEvent, ErrorStreamEvent, MessageStreamEvent, TitleStreamEvent, WaitStreamEvent
from domain.event.plan import PlanStreamEvent
from domain.event.status import PlanEventStatus, StepEventStatus, ToolEventStatus
from domain.event.step import StepStreamEvent
from domain.event.tool import ToolStreamEvent
from domain.task.plan import TaskPlan
from domain.task.step import TaskStep


def _serialize_plan(plan: TaskPlan) -> dict[str, Any]:
    return {
        "plan_id": str(plan.plan_id),
        "title": plan.title,
        "goal": plan.goal,
        "message": plan.message,
        "status": plan.status.value,
        "steps": [
            {
                "step_id": str(step.step_id),
                "description": step.description,
                "agent_role": step.agent_role.value,
                "status": step.status.value,
                "result": step.result,
                "error": step.error,
            }
            for step in plan.steps
        ],
    }


def _serialize_step(step: TaskStep) -> dict[str, Any]:
    return {
        "step_id": str(step.step_id),
        "description": step.description,
        "agent_role": step.agent_role.value,
        "status": step.status.value,
        "success": step.success,
        "result": step.result,
        "attachments": list(step.attachments),
        "error": step.error,
    }


def plan_created(plan: TaskPlan) -> PlanStreamEvent:
    return PlanStreamEvent(plan=_serialize_plan(plan), status=PlanEventStatus.CREATED)


def plan_updated(plan: TaskPlan) -> PlanStreamEvent:
    return PlanStreamEvent(plan=_serialize_plan(plan), status=PlanEventStatus.UPDATED)


def plan_completed(plan: TaskPlan) -> PlanStreamEvent:
    return PlanStreamEvent(plan=_serialize_plan(plan), status=PlanEventStatus.COMPLETED)


def step_started(step: TaskStep) -> StepStreamEvent:
    return StepStreamEvent(step=_serialize_step(step), status=StepEventStatus.STARTED)


def step_completed(step: TaskStep) -> StepStreamEvent:
    return StepStreamEvent(step=_serialize_step(step), status=StepEventStatus.COMPLETED)


def step_failed(step: TaskStep, error: str) -> StepStreamEvent:
    payload = _serialize_step(step)
    payload["error"] = error
    return StepStreamEvent(step=payload, status=StepEventStatus.FAILED)


def user_message(message: str) -> MessageStreamEvent:
    return MessageStreamEvent(role="user", message=message)


def assistant_message(
    message: str,
    *,
    partial: bool = False,
    stream_id: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> MessageStreamEvent:
    return MessageStreamEvent(
        role="assistant",
        message=message,
        partial=partial,
        stream_id=stream_id,
        attachments=list(attachments or []),
    )


def title_event(title: str) -> TitleStreamEvent:
    return TitleStreamEvent(title=title)


def wait_event(*, reason: str = "", question: str = "") -> WaitStreamEvent:
    return WaitStreamEvent(reason=reason, question=question)


def error_event(error: str) -> ErrorStreamEvent:
    return ErrorStreamEvent(error=error)


def done_event() -> DoneStreamEvent:
    return DoneStreamEvent()


def tool_calling(
    *,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    function_args: dict[str, Any],
) -> ToolStreamEvent:
    return ToolStreamEvent(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        function_name=function_name,
        function_args=function_args,
        status=ToolEventStatus.CALLING,
    )


def tool_called(
    *,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    function_args: dict[str, Any],
    function_result: Any,
) -> ToolStreamEvent:
    return ToolStreamEvent(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        function_name=function_name,
        function_args=function_args,
        function_result=function_result,
        status=ToolEventStatus.CALLED,
    )
