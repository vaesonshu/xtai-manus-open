"""LangGraph 可观测性：可选 OpenTelemetry 与结构化日志。"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

_UNSET = object()
_tracer: Any = _UNSET


def _get_tracer():
    """懒加载 OpenTelemetry tracer（未安装时返回 None）。"""
    global _tracer
    if _tracer is not _UNSET:
        return _tracer
    try:
        from opentelemetry import trace

        _tracer = trace.get_tracer("xtai.langgraph")
    except ImportError:
        _tracer = None
    return _tracer


@asynccontextmanager
async def trace_graph_invoke(
    *,
    task_id: str,
    enabled: bool,
    resume: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """包裹图执行：启用时写 OTEL span，否则仅记耗时日志。"""
    if not enabled:
        yield {}
        return

    tracer = _get_tracer()
    started = time.perf_counter()

    if tracer is None:
        logger.info(
            "langgraph.invoke start task_id=%s resume=%s",
            task_id,
            resume,
        )
        try:
            yield {}
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "langgraph.invoke end task_id=%s elapsed_ms=%.1f",
                task_id,
                elapsed_ms,
            )
        return

    with tracer.start_as_current_span(
        "langgraph.invoke",
        attributes={"task_id": task_id, "resume": resume},
    ) as span:
        try:
            yield {"span": span}
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("error", True)
            raise
        finally:
            span.set_attribute(
                "elapsed_ms",
                (time.perf_counter() - started) * 1000,
            )
