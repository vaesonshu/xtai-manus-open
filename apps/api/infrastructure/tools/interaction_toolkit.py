"""人机交互工具集：通知用户与提问。"""

from __future__ import annotations

from langchain_core.tools import tool

from infrastructure.tools.langchain_toolkit import LangChainToolKit


@tool
def message_notify_user(text: str) -> str:
    """向用户发送消息，且无需用户回复。用于进度更新或报告完成情况。"""
    normalized = text.strip()
    return normalized or "Continue"


@tool
def message_ask_user(text: str) -> str:
    """向用户提问并等待回复。需要澄清需求、确认方案或获取额外信息时调用。"""
    normalized = text.strip()
    if not normalized:
        return "请提供您的问题内容。"
    return normalized


def build_interaction_toolkit() -> LangChainToolKit:
    """构建人机交互工具集。"""
    return LangChainToolKit(
        name="interaction",
        tools=[message_notify_user, message_ask_user],
    )
