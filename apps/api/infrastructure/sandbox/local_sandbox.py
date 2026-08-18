"""本地沙箱实现：基于工作目录的文件与 Shell 操作。"""

from __future__ import annotations

import asyncio
import glob as glob_module
import re
from pathlib import Path

from domain.tool.result import ToolResult


class LocalSandbox:
    """进程内本地沙箱，适用于开发与测试。"""

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._shell_outputs: dict[str, str] = {}

    @property
    def workspace_root(self) -> Path:
        return self._root

    def _resolve_path(self, filepath: str) -> Path:
        candidate = Path(filepath)
        if candidate.is_absolute():
            path = candidate.resolve()
        else:
            path = (self._root / filepath).resolve()
        if self._root not in path.parents and path != self._root:
            raise ValueError(f"path escapes sandbox: {filepath}")
        return path

    def _resolve_dir(self, exec_dir: str) -> Path:
        if not exec_dir:
            return self._root
        return self._resolve_path(exec_dir)

    async def exec_command(
        self,
        session_id: str,
        exec_dir: str,
        command: str,
    ) -> ToolResult:
        workdir = self._resolve_dir(exec_dir)
        workdir.mkdir(parents=True, exist_ok=True)
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")
        self._shell_outputs[session_id] = output
        success = process.returncode == 0
        return ToolResult(
            success=success,
            message=output or f"exit code: {process.returncode}",
            data={"exit_code": process.returncode, "session_id": session_id},
        )

    async def read_shell_output(self, session_id: str) -> ToolResult:
        output = self._shell_outputs.get(session_id, "")
        return ToolResult(success=True, message=output, data={"session_id": session_id})

    async def read_file(
        self,
        filepath: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
        max_length: int = 10000,
    ) -> ToolResult:
        path = self._resolve_path(filepath)
        if not path.exists():
            return ToolResult(success=False, message=f"file not found: {filepath}")
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if start_line is not None or end_line is not None:
            start = start_line or 0
            end = end_line if end_line is not None else len(lines)
            text = "\n".join(lines[start:end])
        if len(text) > max_length:
            text = text[:max_length] + "\n...(truncated)"
        return ToolResult(success=True, message=text, data={"filepath": str(path)})

    async def write_file(
        self,
        filepath: str,
        content: str,
        *,
        append: bool = False,
    ) -> ToolResult:
        path = self._resolve_path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        if append and path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(existing + content, encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, message=f"written: {filepath}", data={"filepath": str(path)})

    async def replace_in_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
    ) -> ToolResult:
        path = self._resolve_path(filepath)
        if not path.exists():
            return ToolResult(success=False, message=f"file not found: {filepath}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if old_str not in text:
            return ToolResult(success=False, message="old_str not found in file")
        path.write_text(text.replace(old_str, new_str), encoding="utf-8")
        return ToolResult(success=True, message=f"replaced in {filepath}")

    async def search_in_file(self, filepath: str, regex: str) -> ToolResult:
        path = self._resolve_path(filepath)
        if not path.exists():
            return ToolResult(success=False, message=f"file not found: {filepath}")
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(regex, text)
        return ToolResult(
            success=True,
            message=str(matches),
            data={"match_count": len(matches)},
        )

    async def find_files(self, dir_path: str, glob_pattern: str) -> ToolResult:
        base = self._resolve_path(dir_path)
        if not base.exists():
            return ToolResult(success=False, message=f"directory not found: {dir_path}")
        pattern = str(base / glob_pattern)
        files = glob_module.glob(pattern, recursive=True)
        relative = [str(Path(item).relative_to(self._root)) for item in files]
        return ToolResult(success=True, message=str(relative), data={"files": relative})
