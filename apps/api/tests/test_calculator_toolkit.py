"""计算器工具测试。"""

from __future__ import annotations

import pytest

from infrastructure.tools.calculator_toolkit import build_calculator_toolkit


@pytest.mark.asyncio
async def test_calculate_basic_expression() -> None:
    toolkit = build_calculator_toolkit()
    result = await toolkit.invoke("calculate", {"expression": "(123 + 456) * 7"})
    assert result.success is True
    assert result.message == "4053"


@pytest.mark.asyncio
async def test_calculate_rejects_unsafe_expression() -> None:
    toolkit = build_calculator_toolkit()
    result = await toolkit.invoke("calculate", {"expression": "__import__('os').system('pwd')"})
    assert result.success is False
    assert "不安全" in result.message or "无效" in result.message
