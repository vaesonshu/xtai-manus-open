"""文件附件值对象：用于步骤与消息交付。"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any


@dataclass(frozen=True)
class FileAttachment:
    """文件附件元数据。

    记录用户上传或 Agent 在沙箱中生成的文件，便于 SSE 与前端展示。
    """

    file_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = ""
    filepath: str = ""
    key: str = ""
    extension: str = ""
    mime_type: str = ""
    size: int = 0

    @classmethod
    def from_filepath(cls, filepath: str) -> FileAttachment:
        """从沙箱路径构造附件（LLM 通常只返回 filepath 字符串）。"""
        normalized = filepath.strip()
        if not normalized:
            raise ValueError("filepath must not be empty")

        name = PurePosixPath(normalized.replace("\\", "/")).name
        extension = PurePosixPath(name).suffix.lstrip(".")
        return cls(
            filename=name,
            filepath=normalized,
            extension=extension,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FileAttachment:
        """从字典反序列化，兼容 ``id`` / ``file_id`` 两种键名。"""
        file_id = str(payload.get("id") or payload.get("file_id") or uuid.uuid4())
        filepath = str(payload.get("filepath") or "")
        filename = str(payload.get("filename") or "")
        if not filename and filepath:
            filename = PurePosixPath(filepath.replace("\\", "/")).name

        extension = str(payload.get("extension") or "")
        if not extension and filename:
            extension = PurePosixPath(filename).suffix.lstrip(".")

        return cls(
            file_id=file_id,
            filename=filename,
            filepath=filepath,
            key=str(payload.get("key") or ""),
            extension=extension,
            mime_type=str(payload.get("mime_type") or ""),
            size=int(payload.get("size") or 0),
        )

    @classmethod
    def coerce(cls, value: FileAttachment | dict[str, Any] | str) -> FileAttachment:
        """将路径字符串、字典或已有值对象统一为 ``FileAttachment``。"""
        if isinstance(value, FileAttachment):
            return value
        if isinstance(value, dict):
            return cls.from_dict(value)
        if isinstance(value, str):
            return cls.from_filepath(value)
        raise TypeError(f"unsupported attachment value: {type(value)!r}")

    @classmethod
    def coerce_many(
        cls,
        values: Iterable[FileAttachment | dict[str, Any] | str],
    ) -> tuple[FileAttachment, ...]:
        """批量规范化附件列表。"""
        return tuple(cls.coerce(item) for item in values)

    def to_dict(self) -> dict[str, Any]:
        """序列化为 SSE / API 友好的字典。"""
        return {
            "id": self.file_id,
            "filename": self.filename,
            "filepath": self.filepath,
            "key": self.key,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "size": self.size,
        }


def from_path_strings(paths: Iterable[str]) -> tuple[FileAttachment, ...]:
    """将 LLM 输出的 filepath 字符串列表转为附件元组。"""
    return tuple(FileAttachment.from_filepath(path) for path in paths if path and path.strip())
