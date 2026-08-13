"""表现层依赖：从容器获取装配好的服务。"""

from __future__ import annotations

from functools import lru_cache

from infrastructure import Container, build_container, get_settings


@lru_cache
def get_container() -> Container:
    """获取（缓存的）应用容器。"""
    return build_container(get_settings())
