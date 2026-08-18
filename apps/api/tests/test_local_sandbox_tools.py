"""本地沙箱与工具集测试。"""

from __future__ import annotations

import pytest

from infrastructure.sandbox.local_sandbox import LocalSandbox
from infrastructure.tools.file_toolkit import build_file_toolkit
from infrastructure.tools.shell_toolkit import build_shell_toolkit


@pytest.mark.asyncio
async def test_local_sandbox_file_and_shell(tmp_path) -> None:
    sandbox = LocalSandbox(tmp_path)
    file_toolkit = build_file_toolkit(sandbox)
    shell_toolkit = build_shell_toolkit(sandbox)

    write_result = await file_toolkit.invoke(
        "write_file",
        {"filepath": "notes.txt", "content": "hello sandbox"},
    )
    assert write_result.success is True

    read_result = await file_toolkit.invoke("read_file", {"filepath": "notes.txt"})
    assert "hello sandbox" in read_result.message

    shell_result = await shell_toolkit.invoke(
        "shell_execute",
        {
            "session_id": "s1",
            "exec_dir": str(tmp_path),
            "command": "echo ok",
        },
    )
    assert shell_result.success is True
