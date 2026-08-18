"""带缓存的仓库装饰器：读穿缓存、写时更新缓存。"""

from __future__ import annotations

import json
import logging
from typing import Any

from domain.agent.entity import AgentRun, RunStatus
from domain.ports import AgentRunRepository, CachePort
from domain.primitives import RunId

logger = logging.getLogger(__name__)


def _cache_key(run_id: RunId) -> str:
    return f"agent_run:{run_id}"


def _serialize_run(run: AgentRun) -> str:
    """将聚合根序列化为 JSON 字符串，便于存入 Redis。"""
    payload: dict[str, Any] = {
        "run_id": str(run.run_id),
        "goal": run.goal,
        "status": run.status.value,
        "result": run.result,
        "error": run.error,
    }
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_run(data: str) -> AgentRun:
    """从 JSON 字符串还原聚合根（不含领域事件队列）。"""
    payload = json.loads(data)
    return AgentRun(
        run_id=RunId(payload["run_id"]),
        goal=payload["goal"],
        status=RunStatus(payload["status"]),
        result=payload.get("result", {}),
        error=payload.get("error"),
    )


class CachingAgentRunRepository:
    """``AgentRunRepository`` 的缓存装饰器。

    读取时优先查缓存，未命中再回落到底层仓库并回填；
    写入时同步更新底层仓库与缓存，保证一致性。
    """

    def __init__(
        self,
        repository: AgentRunRepository,
        cache: CachePort,
        *,
        ttl_seconds: int,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    def save(self, run: AgentRun) -> None:
        self._repository.save(run)
        try:
            self._cache.set(_cache_key(run.run_id), _serialize_run(run), self._ttl_seconds)
        except Exception:  # noqa: BLE001 - 缓存故障不应阻断主流程
            logger.warning("缓存写入失败，已跳过", exc_info=True)

    def get(self, run_id: RunId) -> AgentRun | None:
        try:
            cached = self._cache.get(_cache_key(run_id))
            if cached is not None:
                return _deserialize_run(cached)
        except Exception:  # noqa: BLE001 - 缓存故障时回落到底层仓库
            logger.warning("缓存读取失败，回落到底层仓库", exc_info=True)

        run = self._repository.get(run_id)
        if run is not None:
            try:
                self._cache.set(_cache_key(run_id), _serialize_run(run), self._ttl_seconds)
            except Exception:  # noqa: BLE001
                logger.warning("缓存回填失败，已跳过", exc_info=True)
        return run
