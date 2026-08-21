"""StepExecutor 将 tool 事件绑定到当前步骤。"""

from __future__ import annotations

import pytest

from application.agent.step_executor import StepExecutor, StepExecutionContext
from application.agent.step_result import StepExecutionResult
from domain.agent.role import AgentRole
from domain.event import tool_calling
from domain.task.identifiers import TaskId
from domain.task.plan import TaskPlan


class _FakeReactExecutor:
    async def invoke(self, **kwargs):
        on_event = kwargs["on_event"]
        await on_event(
            tool_calling(
                tool_call_id="c1",
                tool_name="mock",
                function_name="echo",
                function_args={"text": "hi"},
            )
        )
        return StepExecutionResult(success=True, result="ok", raw_content="ok")


@pytest.mark.asyncio
async def test_step_executor_injects_step_id_into_tool_events() -> None:
    plan = TaskPlan.create(title="t", goal="g")
    step = plan.add_step("调用工具", agent_role=AgentRole.EXECUTOR)
    events: list = []

    async def on_event(event) -> None:
        events.append(event)

    executor = StepExecutor(_FakeReactExecutor())  # type: ignore[arg-type]
    await executor.execute(
        task_id=TaskId(),
        step=step,
        context=StepExecutionContext(message="g"),
        on_event=on_event,
    )

    assert events[0].step_id == str(step.step_id)
    assert events[0].as_dict()["step_id"] == str(step.step_id)
