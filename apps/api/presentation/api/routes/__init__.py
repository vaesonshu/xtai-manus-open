"""路由汇总。"""

from fastapi import APIRouter

from presentation.api.routes import agents, health, llm, system, tasks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(llm.router)
api_router.include_router(tasks.router)
api_router.include_router(system.router)

__all__ = ["api_router"]
