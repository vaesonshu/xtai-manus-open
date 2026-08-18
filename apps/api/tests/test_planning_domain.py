"""多 Agent 规划领域测试。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.planning import PlanBuilder, PlanStepSpec
from domain.task import AgentTask, ExecutionStatus, TaskPlan


def test_plan_builder_creates_multi_agent_steps() -> None:
    specs = [
        PlanStepSpec(description="收集资料", agent_role=AgentRole.RESEARCHER),
        PlanStepSpec(description="实现脚本", agent_role=AgentRole.CODER),
        PlanStepSpec(description="复核输出", agent_role=AgentRole.REVIEWER),
    ]
    plan = PlanBuilder.build(title="调研任务", goal="分析竞品", step_specs=specs)

    assert len(plan.steps) == 3
    assert plan.steps[0].agent_role is AgentRole.RESEARCHER
    assert plan.steps[2].agent_role is AgentRole.REVIEWER


def test_task_plan_revise_skips_pending_and_adds_new_steps() -> None:
    plan = TaskPlan.create(title="t", goal="分析竞品")
    first = plan.add_step("旧步骤 1", agent_role=AgentRole.EXECUTOR)
    plan.add_step("旧步骤 2", agent_role=AgentRole.EXECUTOR)

    first.start()
    first.complete("done")

    new_steps = plan.revise(
        [
            PlanStepSpec(description="新步骤 A", agent_role=AgentRole.RESEARCHER),
            PlanStepSpec(description="新步骤 B", agent_role=AgentRole.CODER),
        ],
        reason="调研方向变化",
    )

    assert len(new_steps) == 2
    assert plan.steps[1].status is ExecutionStatus.SKIPPED
    assert plan.get_next_step() is new_steps[0]


def test_agent_task_replan_emits_event() -> None:
    task = AgentTask.create(goal="分析竞品")
    task.pull_events()
    plan = TaskPlan.create(title="t", goal="分析竞品")
    plan.add_step("步骤 1", agent_role=AgentRole.RESEARCHER)
    task.attach_plan(plan)
    task.start()

    added = task.replan(
        [PlanStepSpec(description="改做用户访谈", agent_role=AgentRole.RESEARCHER)],
        reason="用户修改需求",
    )
    assert len(added) == 1
    event_names = [event.name for event in task.pull_events()]
    assert "TaskPlanRevised" in event_names
