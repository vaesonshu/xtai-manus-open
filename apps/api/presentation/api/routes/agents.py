"""agent 运行相关路由（遗留 API，薄封装至 /v1/tasks）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from domain.exceptions import NotFoundError
from domain.task.identifiers import TaskId
from infrastructure import Container
from presentation.api.schemas import AgentRunResponse, StartRunRequest
from presentation.deps import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["agents"])


def _task_to_agent_response(container: Container, task_id: str) -> AgentRunResponse:
    """将 Task 聚合根映射为遗留 AgentRunResponse。"""
    task = container.task_service.get(TaskId(task_id))
    return AgentRunResponse(
        run_id=str(task.task_id),
        goal=task.goal,
        status=task.status.value,
        result=task.result,
        error=task.error,
    )


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
    summary="发起 agent 运行（遗留，请使用 POST /v1/tasks）",
)
async def start_run(
    payload: StartRunRequest,
    container: Container = Depends(get_container),
) -> AgentRunResponse:
    """薄封装：委托 ``TaskExecutionApplicationService`` 真正执行。"""
    task_id = await container.task_execution_service.start(payload.goal)
    logger.info("遗留 API /v1/agents/runs 已转发至 task_id=%s", task_id)
    try:
        return _task_to_agent_response(container, task_id)
    except NotFoundError:
        return AgentRunResponse(
            run_id=task_id,
            goal=payload.goal,
            status="running",
        )


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunResponse,
    deprecated=True,
    summary="查询 agent 运行（遗留，请使用 GET /v1/tasks/{task_id}）",
)
def get_run(
    run_id: str,
    container: Container = Depends(get_container),
) -> AgentRunResponse:
    """薄封装：``run_id`` 即 ``task_id``。"""
    return _task_to_agent_response(container, run_id)
