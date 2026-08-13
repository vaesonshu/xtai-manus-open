"""日志系统：统一配置日志等级、输出格式与输出渠道。

设计要点：
- 输出渠道：控制台（彩色文本）、滚动文件（RotatingFileHandler）。
- 输出格式：`text`（人类可读）与 `json`（结构化，便于采集）两种。
- 通过 `Settings` 中的 ``log_*`` 配置项控制，在应用启动时调用
  ``setup_logging`` 一次性装配，之后各模块通过 ``logging.getLogger(__name__)``
  获取已配置好的 logger。
"""

from __future__ import annotations

import copy
import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from infrastructure.config import Settings

# 日志等级名称到 logging 常量的映射
_LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class JsonFormatter(logging.Formatter):
    """结构化 JSON 日志格式器。

    输出单行 JSON，字段包含时间戳、等级、logger 名、消息、异常信息，
    以及通过 ``extra`` 传入的额外字段（如 request_id）。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 附加调用位置
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # 附加通过 extra 传入的结构化字段
        for key in ("request_id", "run_id", "agent_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        # 其他自定义 extra 字段统一归入 extra 对象
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload["extra"] = extra

        return json.dumps(payload, ensure_ascii=False, default=str)


class ColorTextFormatter(logging.Formatter):
    """带 ANSI 颜色的文本格式器（仅控制台使用）。

    为避免污染被多个 handler 共享的 ``LogRecord``，这里复制一份
    record 后仅对副本着色，不影响文件等其他 handler 的输出。
    """

    _COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelno, "")
        colored = copy.copy(record)
        colored.levelname = f"{color}{record.levelname}{self._RESET}"
        return super().format(colored)


# 文本格式：时间 等级 [logger] 消息
_TEXT_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level(level: str) -> int:
    """将配置的等级字符串解析为 logging 常量。"""
    key = level.strip().upper()
    if key not in _LOG_LEVELS:
        return logging.INFO
    return _LOG_LEVELS[key]


def _build_console_handler(settings: Settings) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    elif settings.log_colors:
        handler.setFormatter(ColorTextFormatter(_TEXT_FORMAT, _DATE_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT))
    return handler


def _build_file_handler(settings: Settings) -> logging.Handler:
    path = Path(settings.log_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=str(path),
        maxBytes=settings.log_file_max_bytes,
        backupCount=settings.log_file_backup_count,
        encoding="utf-8",
    )
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT))
    return handler


def setup_logging(settings: Settings) -> None:
    """装配根 logger：清理既有 handler 并按配置挂载新 handler。

    幂等：可重复调用，重复调用会先清空已有 handler 再重新装配。
    """
    root = logging.getLogger()
    root.setLevel(_resolve_level(settings.log_level))

    # 清空已有 handler，避免重复日志
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    if settings.log_console_enabled:
        root.addHandler(_build_console_handler(settings))
    if settings.log_file_enabled:
        root.addHandler(_build_file_handler(settings))

    # 降低第三方库的噪声
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取具名 logger。"""
    return logging.getLogger(name)
