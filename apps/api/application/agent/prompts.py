"""已迁移至 ``application.prompts``，保留兼容导入。"""

from __future__ import annotations

from application.prompts.react import (
    EXECUTION_PROMPT,
    JSON_RESPONSE_FORMAT,
    REACT_SYSTEM_PROMPT,
    SUMMARIZE_PROMPT,
)

__all__ = [
    "EXECUTION_PROMPT",
    "JSON_RESPONSE_FORMAT",
    "REACT_SYSTEM_PROMPT",
    "SUMMARIZE_PROMPT",
]
