"""领域层公共原语：值对象基类、唯一标识、领域事件。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class ValueObject:
    """值对象基类。

    值对象以属性值定义相等性（通过 ``__eq__`` 在子类中实现）。
    """

    __slots__ = ()


@dataclass(frozen=True)
class RunId:
    """agent 运行唯一标识（值对象）。"""

    value: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Timestamp:
    """UTC 时间戳值对象。"""

    value: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def isoformat(self) -> str:
        return self.value.isoformat()


@dataclass
class DomainEvent:
    """领域事件基类。

    领域事件是不可变的、描述已发生事实的记录，用于事件溯源与解耦。
    子类通过 ``@dataclass`` 声明额外字段，并继承 ``run_id`` / ``occurred_at``。
    """

    run_id: RunId
    occurred_at: Timestamp = field(default_factory=Timestamp)

    @property
    def name(self) -> str:
        return type(self).__name__

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "run_id": str(self.run_id),
            "occurred_at": self.occurred_at.isoformat(),
        }
