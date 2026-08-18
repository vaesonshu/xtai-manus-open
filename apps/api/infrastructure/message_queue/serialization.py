"""消息队列载荷序列化：Redis Stream 字段值必须为字符串。"""

from __future__ import annotations

import json
from typing import Any


def encode_message(message: Any) -> str:
    """将任意消息编码为可写入 Stream 的字符串。"""
    if isinstance(message, str):
        return message
    return json.dumps(message, ensure_ascii=False)


def decode_message(raw: Any) -> Any:
    """尝试将 Stream 字段反序列化为 JSON，失败则返回原字符串。"""
    if raw is None:
        return None
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
