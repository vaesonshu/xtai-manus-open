"""plan / replan 节点：调用规划应用服务。"""

from __future__ import annotations

from domain.event import assistant_message, plan_created, plan_updated
from domain.task.identifiers import TaskId
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.helpers import default_offline_specs, require_agent_task
from infrastructure.langgraph.planning_bridge import plan_to_state_steps
from infrastructure.langgraph.state import AgentState


def make_plan_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：创建 plan 节点。"""

    async def plan(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        goal = state["goal"]
        agent_task = require_agent_task(deps, task_id)

        if agent_task.plan is not None:
            return {
                "plan_steps": plan_to_state_steps(agent_task.plan),
                "current_step_index": 0,
                "agent_task_status": agent_task.status.value,
            }

        if state.get("use_llm_planning"):
            task_plan = await deps.planning_service.create_plan(
                task_id=task_id,
                goal=goal,
            )
        else:
            task_plan = deps.planning_service.create_plan_offline(
                goal=goal,
                title=f"规划：{goal}",
                step_specs=default_offline_specs(goal),
            )

        agent_task.attach_plan(task_plan)
        agent_task.start()
        deps.task_repository.save(agent_task)

        await emitter.emit(plan_created(task_plan))
        if task_plan.message:
            await emitter.emit(assistant_message(task_plan.message))

        return {
            "plan_steps": plan_to_state_steps(task_plan),
            "plan": task_plan.title,
            "current_step_index": 0,
            "agent_task_status": agent_task.status.value,
        }

    return plan


def make_replan_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：创建 replan 节点（每步完成后动态修订规划）。"""

    async def replan(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        agent_task = require_agent_task(deps, task_id)
        if agent_task.plan is None:
            return {}

        completed = next(
            (step for step in reversed(agent_task.plan.steps) if step.done),
            None,
        )
        if completed is None:
            return {}

        await deps.planning_service.update_plan_after_step(agent_task, completed)
        deps.task_repository.save(agent_task)
        if agent_task.plan is not None:
            await emitter.emit(plan_updated(agent_task.plan))
            return {"plan_steps": plan_to_state_steps(agent_task.plan)}
        return {}

    return replan
