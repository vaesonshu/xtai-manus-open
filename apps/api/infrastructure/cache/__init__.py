"""缓存基础设施导出。"""

from infrastructure.cache.null_cache import NullCache
from infrastructure.cache.redis_cache import RedisCache

__all__ = ["NullCache", "RedisCache"]
