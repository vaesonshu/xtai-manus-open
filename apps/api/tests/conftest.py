"""测试公共 fixture。"""

from __future__ import annotations

import pytest

from infrastructure.config import get_settings
from presentation.deps import get_container


@pytest.fixture(autouse=True)
def disable_external_services_in_tests(monkeypatch: pytest.MonkeyPatch):
    """测试环境默认关闭 Redis / PostgreSQL，避免依赖外部服务。"""
    monkeypatch.setenv("REDIS_ENABLED", "false")
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    get_settings.cache_clear()
    get_container.cache_clear()
    yield
    get_settings.cache_clear()
    get_container.cache_clear()
