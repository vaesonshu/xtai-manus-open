"""事件总线实现：收集领域事件并分发给订阅者。"""

from __future__ import annotations

import logging
from collections.abc import Callable

from domain.primitives import DomainEvent, IntegrationEvent

logger = logging.getLogger(__name__)

BusEvent = DomainEvent | IntegrationEvent
EventHandler = Callable[[BusEvent], None]


class InMemoryEventBus:
    """基于内存的事件总线，支持按事件类型注册订阅者。"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: BusEvent) -> None:
        for handler in self._handlers.get(event.name, []):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - 事件处理不应阻断主流程
                logger.exception("事件处理失败: %s", event.name)
