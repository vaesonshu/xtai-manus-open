"""init_task 节点：创建任务聚合根并记录用户目标。"""

from __future__ import annotations

from domain.agent.role import AgentRole
from domain.event import user_message
from domain.memory.kind import MemoryKind
from domain.task.identifiers import TaskId
from domain.task.status import TaskStatus
from domain.task.task import AgentTask
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.helpers import require_agent_task
from infrastructure.langgraph.state import AgentState


def make_init_task_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：创建 init_task 节点。"""

    async def init_task(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        goal = state["goal"]
        agent_task = deps.task_repository.get(task_id)

        if agent_task is None:
            agent_task = AgentTask.create(goal=goal, task_id=task_id)
            deps.task_repository.save(agent_task)
            await emitter.emit(user_message(goal))
            deps.memory_service.add_agent_message(
                task_id,
                AgentRole.COORDINATOR,
                {"role": "user", "content": goal},
            )
            deps.memory_service.record(
                task_id,
                kind=MemoryKind.EPISODIC,
                content=f"用户目标：{goal}",
                agent_role=AgentRole.COORDINATOR,
            )
            return {"agent_task_status": agent_task.status.value}

        if agent_task.status is TaskStatus.RUNNING:
            deps.memory_service.rollback_for_user_input(
                task_id,
                AgentRole.COORDINATOR,
                goal,
            )
            await emitter.emit(user_message(goal))
            return {"goal": goal, "agent_task_status": agent_task.status.value}

        require_agent_task(deps, task_id)
        return {"agent_task_status": agent_task.status.value}

    return init_task
