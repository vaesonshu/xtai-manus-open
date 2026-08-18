"""文件工具集：沙箱内文件读写与搜索。"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from domain.ports.sandbox import SandboxPort
from infrastructure.tools.langchain_toolkit import LangChainToolKit


def build_file_toolkit(sandbox: SandboxPort) -> LangChainToolKit:
    """构建文件工具集。"""

    @tool
    async def read_file(
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_length: int = 10000,
    ) -> str:
        """读取文件内容。用于检查文件、分析日志或读取配置。"""
        result = await sandbox.read_file(
            filepath,
            start_line=start_line,
            end_line=end_line,
            max_length=max_length,
        )
        return result.to_tool_content()

    @tool
    async def write_file(filepath: str, content: str, append: bool = False) -> str:
        """写入或追加文件内容。用于创建或修改文件。"""
        result = await sandbox.write_file(filepath, content, append=append)
        return result.to_tool_content()

    @tool
    async def replace_in_file(filepath: str, old_str: str, new_str: str) -> str:
        """在文件中替换指定字符串。"""
        result = await sandbox.replace_in_file(filepath, old_str, new_str)
        return result.to_tool_content()

    @tool
    async def search_in_file(filepath: str, regex: str) -> str:
        """在文件内容中搜索正则匹配。"""
        result = await sandbox.search_in_file(filepath, regex)
        return result.to_tool_content()

    @tool
    async def find_files(dir_path: str, glob_pattern: str) -> str:
        """在目录中按 glob 模式查找文件。"""
        result = await sandbox.find_files(dir_path, glob_pattern)
        return result.to_tool_content()

    return LangChainToolKit(
        name="file",
        tools=[read_file, write_file, replace_in_file, search_in_file, find_files],
    )
