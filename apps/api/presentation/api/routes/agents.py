"""agent 运行相关路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from application.agent.dto import StartAgentRunCommand
from infrastructure import Container
from presentation.api.schemas import AgentRunResponse, StartRunRequest
from presentation.deps import get_container

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_run(
    payload: StartRunRequest,
    container: Container = Depends(get_container),
) -> AgentRunResponse:
    """发起一次 agent 运行（登记并进入异步编排）。"""
    dto = container.agent_service.start(StartAgentRunCommand(goal=payload.goal))
    return AgentRunResponse(
        run_id=dto.run_id,
        goal=dto.goal,
        status=dto.status.value,
        result=dto.result,
        error=dto.error,
    )


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_run(
    run_id: str,
    container: Container = Depends(get_container),
) -> AgentRunResponse:
    """按 ID 查询运行状态。"""
    dto = container.agent_service.get(run_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="run not found")
    return AgentRunResponse(
        run_id=dto.run_id,
        goal=dto.goal,
        status=dto.status.value,
        result=dto.result,
        error=dto.error,
    )
