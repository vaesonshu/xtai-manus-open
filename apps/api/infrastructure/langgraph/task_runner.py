"""LangGraph 任务运行器：实现 ``TaskRunnerPort``。"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from application.memory.service import MemoryApplicationService
from domain.event import error_event
from domain.ports.task import TaskRepository
from domain.task.identifiers import TaskId
from domain.task.ports import TaskExecutionPort
from domain.task.status import TaskStatus
from infrastructure.config import Settings
from infrastructure.langgraph.context import bind_execution, reset_execution
from infrastructure.langgraph.event_emitter import GraphEventEmitter
from infrastructure.langgraph.tracing import trace_graph_invoke

logger = logging.getLogger(__name__)


class LangGraphTaskRunner:
    """使用 LangGraph StateGraph 驱动任务规划与执行。"""

    def __init__(
        self,
        *,
        graph: CompiledStateGraph,
        memory_service: MemoryApplicationService,
        task_repository: TaskRepository,
        event_emitter: GraphEventEmitter,
        checkpointer: BaseCheckpointSaver,
        settings: Settings,
    ) -> None:
        self._graph = graph
        self._memory = memory_service
        self._tasks = task_repository
        self._emitter = event_emitter
        self._checkpointer = checkpointer
        self._settings = settings

    def should_keep_execution_alive(self, task_id: TaskId) -> bool:
        """WAITING 时保留执行实例，供用户 reply 后续跑。"""
        agent_task = self._tasks.get(task_id)
        return agent_task is not None and agent_task.status is TaskStatus.WAITING

    async def invoke(self, execution: TaskExecutionPort) -> None:
        """驱动一次任务执行（新建或从 WAITING / interrupt 恢复）。"""
        task_id = TaskId(execution.task_id)
        agent_task = self._tasks.get(task_id)
        config = self._build_config(task_id)
        token = bind_execution(execution)

        try:
            if agent_task is not None and agent_task.status is TaskStatus.WAITING:
                user_input = await self._read_input(execution)
                await self._run_graph(
                    execution,
                    Command(resume=user_input),
                    config,
                    resume=True,
                )
                return

            payload = await self._read_input(execution)
            goal = payload.get("goal") or payload.get("content") or ""
            initial_state: dict[str, Any] = {
                "goal": goal,
                "task_id": str(task_id),
                "replan_enabled": self._settings.agent_use_llm_planning,
                "use_llm_planning": self._settings.agent_use_llm_planning,
                "max_iterations": self._settings.agent_max_iterations,
                "current_step_index": 0,
                "resume_step": False,
            }
            await self._run_graph(execution, initial_state, config, resume=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception("LangGraph 任务[%s]执行异常", task_id)
            await self._emitter.emit_to(execution, error_event(str(exc)))
            if agent_task is not None and agent_task.status is TaskStatus.RUNNING:
                agent_task.fail(str(exc))
                self._tasks.save(agent_task)
        finally:
            reset_execution(token)

    async def destroy(self) -> None:
        """释放运行器资源。"""
        return None

    async def on_done(self, execution: TaskExecutionPort) -> None:
        """任务结束：压缩记忆（WAITING 时跳过）。"""
        task_id = TaskId(execution.task_id)
        agent_task = self._tasks.get(task_id)
        if agent_task is not None and agent_task.status is TaskStatus.WAITING:
            logger.info("任务[%s]处于等待用户输入，跳过 on_done 清理", task_id)
            return
        self._memory.clear_working(task_id)
        self._memory.compact_conversations(task_id)
        logger.info("任务[%s]执行结束，记忆已压缩", task_id)

    async def _run_graph(
        self,
        execution: TaskExecutionPort,
        input_state: dict[str, Any] | Command,
        config: dict[str, Any],
        *,
        resume: bool = False,
    ) -> None:
        """执行图并在 interrupt 时自然挂起。"""
        async with trace_graph_invoke(
            task_id=execution.task_id,
            enabled=self._settings.langgraph_tracing_enabled,
            resume=resume,
        ):
            result = await self._graph.ainvoke(input_state, config=config)
        if isinstance(result, dict) and result.get("__interrupt__"):
            logger.info("任务[%s]在 interrupt 处挂起，等待用户输入", execution.task_id)

    @staticmethod
    def _build_config(task_id: TaskId) -> dict[str, Any]:
        return {"configurable": {"thread_id": str(task_id)}}

    @staticmethod
    async def _read_input(execution: TaskExecutionPort) -> dict[str, str]:
        """从输入流读取 goal 或用户回复。"""
        _message_id, payload = await execution.input_stream.get(block_ms=5000)
        if isinstance(payload, dict):
            goal = str(payload.get("goal") or payload.get("content") or "").strip()
            if goal:
                return {"goal": goal, "content": goal}
        if isinstance(payload, str) and payload.strip():
            text = payload.strip()
            return {"goal": text, "content": text}
        return {"goal": "未指定目标", "content": "未指定目标"}
