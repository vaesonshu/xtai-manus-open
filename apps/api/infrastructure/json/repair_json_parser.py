"""基于 json-repair 的 JSON 解析器实现。"""

from __future__ import annotations

import logging
from typing import Any

import json_repair

from domain.ports.json_parser import JsonParserPort

logger = logging.getLogger(__name__)


class RepairJsonParser:
    """使用 json-repair 修复并解析 LLM 输出的 JSON 文本。"""

    async def invoke(
        self,
        text: str,
        *,
        default_value: Any | None = None,
    ) -> Any:
        if not text or not text.strip():
            if default_value is not None:
                return default_value
            raise ValueError("json 文本为空，且无默认值")

        logger.debug("解析 JSON 文本: %s", text[:200])
        return json_repair.repair_json(text, return_objects=True)
