"""沙箱执行端口：Shell 与文件操作的抽象。"""

from __future__ import annotations

from typing import Protocol

from domain.tool.result import ToolResult


class SandboxPort(Protocol):
    """本地或远程沙箱的统一端口。"""

    async def exec_command(
        self,
        session_id: str,
        exec_dir: str,
        command: str,
    ) -> ToolResult:
        """在指定目录执行 Shell 命令。"""
        ...

    async def read_shell_output(self, session_id: str) -> ToolResult:
        """读取 Shell 会话输出。"""
        ...

    async def read_file(
        self,
        filepath: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
        max_length: int = 10000,
    ) -> ToolResult:
        """读取文件内容。"""
        ...

    async def write_file(
        self,
        filepath: str,
        content: str,
        *,
        append: bool = False,
    ) -> ToolResult:
        """写入文件。"""
        ...

    async def replace_in_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
    ) -> ToolResult:
        """替换文件中的字符串。"""
        ...

    async def search_in_file(self, filepath: str, regex: str) -> ToolResult:
        """在文件中搜索正则匹配。"""
        ...

    async def find_files(self, dir_path: str, glob_pattern: str) -> ToolResult:
        """按 glob 模式查找文件。"""
        ...
