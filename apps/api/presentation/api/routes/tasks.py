"""Task 执行相关路由：创建、查询、SSE 流与用户回复。"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from application.task.execution_service import TaskExecutionApplicationService
from application.task.service import TaskApplicationService
from domain.task.identifiers import TaskId
from infrastructure import Container
from presentation.api.mappers.task_mapper import to_task_response
from presentation.api.schemas import ReplyTaskRequest, StartTaskRequest, TaskResponse
from presentation.api.stream_event_schemas import validate_stream_event_payload
from presentation.deps import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


def _get_task_service(container: Container = Depends(get_container)) -> TaskApplicationService:
    return container.task_service


def _get_execution_service(
    container: Container = Depends(get_container),
) -> TaskExecutionApplicationService:
    return container.task_execution_service


def _format_sse(payload: dict) -> str:
    """SSE 单条事件格式（出站前校验契约）。"""
    try:
        validated = validate_stream_event_payload(payload)
    except Exception:  # noqa: BLE001 - 单条脏数据不应中断整段 SSE
        logger.warning("跳过无效 SSE 事件: type=%s", payload.get("type"))
        validated = payload
    return f"data: {json.dumps(validated, ensure_ascii=False)}\n\n"


async def _stream_task_events(
    task_id: str,
    execution_service: TaskExecutionApplicationService,
    task_service: TaskApplicationService,
) -> AsyncIterator[str]:
    """回放并持续推送任务输出事件，直到 done / wait / 任务结束。"""
    output = execution_service.output_stream_for(task_id)
    last_id: str | None = None

    async for message_id, payload in output.get_range():
        if not isinstance(payload, dict):
            continue
        yield _format_sse(payload)
        last_id = message_id
        if payload.get("type") in {"done", "wait", "error"}:
            return

    idle_rounds = 0
    while idle_rounds < 120:
        message_id, payload = await output.get(start_id=last_id, block_ms=2000)
        if payload is None:
            try:
                task = task_service.get(TaskId(task_id))
            except Exception:  # noqa: BLE001
                break
            if task.status.value in {"completed", "failed", "cancelled"}:
                idle_rounds += 1
                if idle_rounds >= 3:
                    break
            continue

        idle_rounds = 0
        if not isinstance(payload, dict):
            last_id = message_id
            continue

        yield _format_sse(payload)
        last_id = message_id
        if payload.get("type") in {"done", "wait", "error"}:
            return


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_task(
    payload: StartTaskRequest,
    execution_service: TaskExecutionApplicationService = Depends(_get_execution_service),
    task_service: TaskApplicationService = Depends(_get_task_service),
) -> TaskResponse:
    """提交 Agent 任务并在后台执行（模型 + 工具）。"""
    task_id = await execution_service.start(payload.goal)

    try:
        return to_task_response(task_service.get(TaskId(task_id)))
    except Exception:  # noqa: BLE001
        # Runner 异步启动，聚合根可能尚未写入仓库
        return TaskResponse(task_id=task_id, goal=payload.goal, status="running")


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    task_service: TaskApplicationService = Depends(_get_task_service),
) -> TaskResponse:
    """查询任务当前状态与规划。"""
    return to_task_response(task_service.get(TaskId(task_id)))


@router.get("/{task_id}/stream")
async def stream_task(
    task_id: str,
    execution_service: TaskExecutionApplicationService = Depends(_get_execution_service),
    task_service: TaskApplicationService = Depends(_get_task_service),
) -> StreamingResponse:
    """SSE 推送任务执行事件（plan / step / tool / message / wait / done）。"""
    task_service.get(TaskId(task_id))
    return StreamingResponse(
        _stream_task_events(task_id, execution_service, task_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{task_id}/reply", response_model=TaskResponse)
async def reply_task(
    task_id: str,
    payload: ReplyTaskRequest,
    execution_service: TaskExecutionApplicationService = Depends(_get_execution_service),
    task_service: TaskApplicationService = Depends(_get_task_service),
) -> TaskResponse:
    """任务 WAITING 时提交用户回复并继续执行。"""
    await execution_service.reply(task_id, payload.content)
    return to_task_response(task_service.get(TaskId(task_id)))
