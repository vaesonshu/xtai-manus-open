"""LLM adapter: 通过可热更新的 LlmRuntime 获取 ChatOpenAI。"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from infrastructure.llm.runtime import LlmRuntime

_runtime: LlmRuntime | None = None


def bind_runtime(runtime: LlmRuntime) -> None:
    """在应用启动时装配全局运行时（由容器调用）。"""
    global _runtime
    _runtime = runtime


def get_llm() -> ChatOpenAI:
    """获取当前配置下的 ChatOpenAI 实例。"""
    if _runtime is None:
        raise RuntimeError("LlmRuntime 尚未初始化，请检查容器装配")
    return _runtime.get_chat_model()
