"""SQLite checkpointer 封装：为 LangGraph 提供断点续跑与状态持久化。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from infrastructure.config import get_settings


@lru_cache
def get_checkpointer() -> SqliteSaver:
    """创建（缓存的）SQLite checkpointer。

    使用 ``checkpoint_db_path`` 指定的文件，目录不存在时自动创建。
    """
    settings = get_settings()
    path = Path(settings.checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(path))
