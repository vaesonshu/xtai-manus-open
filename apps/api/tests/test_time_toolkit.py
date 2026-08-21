"""时间工具测试。"""

from __future__ import annotations

import re

import pytest

from infrastructure.tools.time_toolkit import build_time_toolkit


@pytest.mark.asyncio
async def test_get_current_time_returns_timestamp() -> None:
    toolkit = build_time_toolkit()
    result = await toolkit.invoke("get_current_time", {})
    assert result.success is True
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result.message)
