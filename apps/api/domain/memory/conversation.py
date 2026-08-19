"""对话式记忆：按 Agent 隔离的消息列表，支持压缩与回滚。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.memory.constants import MESSAGE_ASK_USER_TOOL

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

    @staticmethod
    def get_message_role(message: dict[str, Any]) -> str | None:
        """读取 ChatML 消息的 role 字段（集中解析，便于后续适配多 LLM 格式）。"""
        return message.get("role")

    def roll_back(self) -> None:
        """回滚最后一条消息（工具调用失败等场景）。"""
        if self.messages:
            self.messages = self.messages[:-1]

    def roll_back_for_user_input(self, user_content: str) -> None:
        """用户续聊时的智能回滚。

        - 若最后一条 assistant 消息包含 ``message_ask_user`` 工具调用：
          追加 tool 回复（用户输入），保持对话连贯。
        - 否则：删除最后一条消息，避免重复上下文。
        """
        if not user_content.strip():
            return

        last = self.get_last_message()
        if last is None:
            return

        tool_calls = last.get("tool_calls") or []
        if tool_calls:
            ask_call = self._find_ask_user_call(tool_calls)
            if ask_call is not None:
                tool_call_id = ask_call.get("id") or ""
                self.add_message(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "function_name": MESSAGE_ASK_USER_TOOL,
                        "content": user_content.strip(),
                    }
                )
                return

        if self.get_message_role(last) != "user":
            self.roll_back()

    @staticmethod
    def _find_ask_user_call(tool_calls: list[dict[str, Any]]) -> dict[str, Any] | None:
        """查找 ``message_ask_user`` 工具调用。"""
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            if function.get("name") == MESSAGE_ASK_USER_TOOL:
                return tool_call
        return None

    def compact(self) -> None:
        """压缩记忆中的冗余内容，降低 LLM 上下文占用。"""
        for message in self.messages:
            if self.get_message_role(message) == "tool":
                function_name = message.get("function_name") or message.get("name")
                if function_name in _COMPACT_TOOL_NAMES:
                    message["content"] = "(removed)"
            # reasoning 字段仅用于调试，压缩时移除
            message.pop("reasoning_content", None)
