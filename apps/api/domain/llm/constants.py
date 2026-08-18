"""LLM 领域常量。"""

from __future__ import annotations

# 当前支持的提供商标识（与 infrastructure 层注册表保持一致）
SUPPORTED_LLM_PROVIDERS: frozenset[str] = frozenset(
    {
        "openai",
        "openai_compatible",
    }
)
