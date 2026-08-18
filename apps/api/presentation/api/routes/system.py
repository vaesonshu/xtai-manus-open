"""系统级路由：健康扩展、LangGraph 图可视化等。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from infrastructure import Container
from infrastructure.langgraph.visualization import export_mermaid
from presentation.deps import get_container

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get("/langgraph/mermaid", response_class=PlainTextResponse)
def langgraph_mermaid(
    container: Container = Depends(get_container),
) -> str:
    """导出当前 LangGraph 编排图的 Mermaid 文本（调试用）。"""
    graph = container.agent_graph
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LangGraph 未启用（AGENT_ORCHESTRATOR!=langgraph）",
        )
    return export_mermaid(graph)
