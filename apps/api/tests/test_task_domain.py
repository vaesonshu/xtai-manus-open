"""Task 领域模型测试。"""

from __future__ import annotations

from domain.exceptions import ConflictError
from domain.task import (
    AgentTask,
    ExecutionStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)


def test_task_plan_get_next_step() -> None:
    plan = TaskPlan.create(title="调研", goal="分析竞品")
    step1 = plan.add_step("收集资料")
    plan.add_step("撰写报告")

    assert plan.get_next_step() is step1
    step1.start()
    step1.complete("done")
    assert plan.get_next_step() is not None
    assert plan.get_next_step().description == "撰写报告"


def test_agent_task_lifecycle_with_plan() -> None:
    task = AgentTask.create(goal="分析竞品")
    task.pull_events()

    plan = TaskPlan.create(title="竞品分析", goal="分析竞品")
    plan.add_step("收集公开资料")
    plan.add_step("输出对比表")
    task.attach_plan(plan)

    task.start()
    step = task.begin_next_step()
    assert step.description == "收集公开资料"
    task.complete_current_step("已收集 5 份资料")

    step = task.begin_next_step()
    assert step.description == "输出对比表"
    task.complete_current_step("对比表已完成")

    task.complete(result={"summary": "完成竞品分析"})
    assert task.status is TaskStatus.COMPLETED
    assert task.plan is not None
    assert task.plan.status is ExecutionStatus.COMPLETED

    event_names = [event.name for event in task.pull_events()]
    assert "TaskPlanAttached" in event_names
    assert "TaskStepStarted" in event_names
    assert "TaskStepCompleted" in event_names
    assert "TaskCompleted" in event_names


def test_agent_task_wait_and_resume() -> None:
    task = AgentTask.create(goal="需要用户确认")
    task.pull_events()
    task.start()
    task.wait_for_input(reason="等待用户选择方案")
    assert task.status is TaskStatus.WAITING
    task.resume()
    assert task.status is TaskStatus.RUNNING


def test_step_failure_cascades_to_task() -> None:
    task = AgentTask.create(goal="执行失败场景")
    task.pull_events()
    plan = TaskPlan.create(title="t", goal="执行失败场景")
    plan.add_step("会失败的步骤")
    task.attach_plan(plan)
    task.start()
    task.begin_next_step()
    task.fail_current_step("tool timeout")

    assert task.status is TaskStatus.FAILED
    assert task.plan is not None
    assert task.plan.status is ExecutionStatus.FAILED


def test_cannot_attach_plan_twice() -> None:
    task = AgentTask.create(goal="重复挂载")
    plan = TaskPlan.create(title="p", goal="重复挂载")
    plan.add_step("s1")
    task.attach_plan(plan)
    try:
        task.attach_plan(plan)
    except ConflictError:
        pass
    else:
        raise AssertionError("expected ConflictError")
