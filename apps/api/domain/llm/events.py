"""LLM 相关集成事件。"""

from __future__ import annotations

from dataclasses import dataclass

from domain.primitives import IntegrationEvent


@dataclass
class LlmConfigUpdated(IntegrationEvent):
    """LLM 配置已更新，运行时需热加载新参数。"""

    config_id: str = ""
