"""时间工具集：获取当前日期时间。"""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from infrastructure.tools.langchain_toolkit import LangChainToolKit


@tool
def get_current_time() -> str:
    """获取当前本地日期和时间。需要准确时刻、日期或时区信息时必须调用本工具。"""
    now = datetime.now().astimezone()
    tz_name = now.tzname() or ""
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    return f"{stamp} {tz_name}".strip()


def build_time_toolkit() -> LangChainToolKit:
    """构建时间工具集。"""
    return LangChainToolKit(name="time", tools=[get_current_time])
