"""LangGraph 节点共享辅助函数。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.task.identifiers import TaskId
from domain.task.status import ExecutionStatus
from domain.task.step import TaskStep
from domain.task.task import AgentTask
from infrastructure.langgraph.dependencies import GraphNodeDependencies


def require_agent_task(deps: GraphNodeDependencies, task_id: TaskId) -> AgentTask:
    """从仓储读取任务，不存在时抛错。"""
    agent_task = deps.task_repository.get(task_id)
    if agent_task is None:
        raise RuntimeError(f"agent task not found: {task_id}")
    return agent_task


def get_running_step(agent_task: AgentTask) -> TaskStep | None:
    """获取当前运行中的步骤（WAITING 恢复时使用）。"""
    if agent_task.plan is None:
        return None
    return next(
        (
            item
            for item in agent_task.plan.steps
            if item.status is ExecutionStatus.RUNNING
        ),
        None,
    )


def default_offline_specs(goal: str):
    """离线规划默认三步（与 AgentTaskRunner 对齐）。"""
    from domain.planning.step_spec import PlanStepSpec

    return [
        PlanStepSpec(
            description=f"调研并收集与「{goal}」相关的资料",
            agent_role=AgentRole.RESEARCHER,
        ),
        PlanStepSpec(
            description="整理方案并生成可交付输出",
            agent_role=AgentRole.CODER,
        ),
        PlanStepSpec(
            description="复核输出质量与完整性",
            agent_role=AgentRole.REVIEWER,
        ),
    ]
