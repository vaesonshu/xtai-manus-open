"""FileAttachment 值对象测试。"""

from __future__ import annotations

import pytest

from domain.file.attachment import FileAttachment, from_path_strings


def test_from_filepath_derives_filename_and_extension() -> None:
    attachment = FileAttachment.from_filepath("/workspace/output/report.md")

    assert attachment.filename == "report.md"
    assert attachment.filepath == "/workspace/output/report.md"
    assert attachment.extension == "md"
    assert attachment.file_id


def test_to_dict_uses_id_key() -> None:
    attachment = FileAttachment.from_filepath("/tmp/demo.txt")
    payload = attachment.to_dict()

    assert payload["id"] == attachment.file_id
    assert payload["filename"] == "demo.txt"
    assert payload["filepath"] == "/tmp/demo.txt"


def test_from_dict_supports_legacy_id_field() -> None:
    attachment = FileAttachment.from_dict(
        {
            "id": "file-1",
            "filename": "a.pdf",
            "filepath": "/workspace/a.pdf",
            "key": "cos/key/a.pdf",
            "mime_type": "application/pdf",
            "size": 128,
        }
    )

    assert attachment.file_id == "file-1"
    assert attachment.key == "cos/key/a.pdf"
    assert attachment.mime_type == "application/pdf"
    assert attachment.size == 128


def test_coerce_many_accepts_strings_and_dicts() -> None:
    attachments = FileAttachment.coerce_many(
        [
            "/workspace/a.md",
            {"id": "b", "filepath": "/workspace/b.md", "filename": "b.md"},
        ]
    )

    assert len(attachments) == 2
    assert attachments[0].filename == "a.md"
    assert attachments[1].file_id == "b"


def test_from_path_strings_skips_empty_entries() -> None:
    attachments = from_path_strings(["/workspace/a.md", "", "  "])

    assert len(attachments) == 1
    assert attachments[0].filepath == "/workspace/a.md"


def test_from_filepath_rejects_empty_path() -> None:
    with pytest.raises(ValueError, match="filepath"):
        FileAttachment.from_filepath("   ")
