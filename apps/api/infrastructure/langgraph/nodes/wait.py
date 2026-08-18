"""wait_interrupt 节点：人机协作断点。"""

from __future__ import annotations

from langgraph.types import interrupt

from domain.agent.role import AgentRole
from domain.event import assistant_message, wait_event
from domain.task.identifiers import TaskId
from domain.task.status import TaskStatus
from infrastructure.langgraph.dependencies import GraphNodeDependencies
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.nodes.helpers import require_agent_task
from infrastructure.langgraph.state import AgentState


def make_wait_interrupt_node(
    deps: GraphNodeDependencies,
    emitter: GraphEventEmitter,
):
    """工厂：等待用户输入并在 checkpointer 上挂起。"""

    async def wait_interrupt(state: AgentState) -> dict:
        task_id = TaskId(state["task_id"])
        question = str(state.get("waiting_question") or "请补充信息")
        role_value = state.get("waiting_agent_role")
        agent_role = (
            AgentRole.from_value(str(role_value))
            if role_value
            else AgentRole.COORDINATOR
        )

        agent_task = require_agent_task(deps, task_id)
        # 首次进入：标记 WAITING 并推送事件；interrupt 恢复后节点会重入，此时跳过
        if agent_task.status is TaskStatus.RUNNING:
            agent_task.wait_for_input(question, agent_role=agent_role)
            deps.task_repository.save(agent_task)
            await emitter.emit(wait_event(reason=question, question=question))
            await emitter.emit(assistant_message(question))

        # LangGraph interrupt：恢复时 Command(resume=...) 的值作为返回值
        user_reply = interrupt(question)

        return {
            "user_reply": str(user_reply),
            "waiting_question": None,
            "waiting_agent_role": None,
            "agent_task_status": agent_task.status.value,
        }

    return wait_interrupt
