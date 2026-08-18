"""对话式记忆：按 Agent 隔离的消息列表，支持压缩与回滚。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 工具执行结果过大时，压缩为占位符（避免上下文爆炸）
_COMPACT_TOOL_NAMES = frozenset(
    {
        "browser_view",
        "browser_navigate",
        "web_search",
        "fetch_url",
    }
)


@dataclass
class ConversationMemory:
    """单个 Agent 的对话记忆（ChatML 风格消息列表）。"""

    messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return len(self.messages) == 0

    def add_message(self, message: dict[str, Any]) -> None:
        """追加一条消息。"""
        self.messages.append(dict(message))

    def add_messages(self, messages: list[dict[str, Any]]) -> None:
        """批量追加消息。"""
        self.messages.extend(dict(item) for item in messages)

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self.messages)

    def get_last_message(self) -> dict[str, Any] | None:
        return self.messages[-1] if self.messages else None

    def roll_back(self) -> None:
        """回滚最后一条消息（工具调用失败等场景）。"""
        if self.messages:
            self.messages = self.messages[:-1]

    def compact(self) -> None:
        """压缩记忆中的冗余内容，降低 LLM 上下文占用。"""
        for message in self.messages:
            role = message.get("role")
            if role == "tool":
                function_name = message.get("function_name") or message.get("name")
                if function_name in _COMPACT_TOOL_NAMES:
                    message["content"] = "(removed)"
            # reasoning 字段仅用于调试，压缩时移除
            message.pop("reasoning_content", None)
