"""LLM 配置相关路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from application.llm.dto import LlmConfigDTO, UpdateLlmConfigCommand
from infrastructure import Container
from presentation.api.schemas import LlmConfigResponse, UpdateLlmConfigRequest
from presentation.deps import get_container

router = APIRouter(prefix="/v1/llm", tags=["llm"])


def _to_response(dto: LlmConfigDTO) -> LlmConfigResponse:
    """将应用层 DTO 转为 HTTP 响应模型。"""
    return LlmConfigResponse(
        config_id=dto.config_id,
        provider=dto.provider,
        model=dto.model,
        base_url=dto.base_url,
        temperature=dto.temperature,
        max_tokens=dto.max_tokens,
        timeout_seconds=dto.timeout_seconds,
        api_key_masked=dto.api_key_masked,
        has_api_key=dto.has_api_key,
    )


@router.get("/config", response_model=LlmConfigResponse)
def get_llm_config(
    container: Container = Depends(get_container),
) -> LlmConfigResponse:
    """获取当前 LLM 配置（API Key 脱敏）。"""
    return _to_response(container.llm_config_service.get_config())


@router.put("/config", response_model=LlmConfigResponse)
def update_llm_config(
    payload: UpdateLlmConfigRequest,
    container: Container = Depends(get_container),
) -> LlmConfigResponse:
    """更新 LLM 配置并热加载运行时。"""
    dto = container.llm_config_service.update_config(
        UpdateLlmConfigCommand(
            provider=payload.provider,
            model=payload.model,
            api_key=payload.api_key,
            base_url=payload.base_url,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            timeout_seconds=payload.timeout_seconds,
            clear_max_tokens=payload.clear_max_tokens,
        )
    )
    return _to_response(dto)
