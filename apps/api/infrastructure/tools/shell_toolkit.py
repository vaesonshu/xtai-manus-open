"""Shell 工具集：沙箱命令执行。"""

from __future__ import annotations

from langchain_core.tools import tool

from domain.ports.sandbox import SandboxPort
from infrastructure.tools.langchain_toolkit import LangChainToolKit


def build_shell_toolkit(sandbox: SandboxPort) -> LangChainToolKit:
    """构建 Shell 工具集。"""

    @tool
    async def shell_execute(session_id: str, exec_dir: str, command: str) -> str:
        """在指定 Shell 会话中执行命令。可用于运行代码、安装依赖或文件管理。"""
        result = await sandbox.exec_command(session_id, exec_dir, command)
        return result.to_tool_content()

    @tool
    async def shell_read_output(session_id: str) -> str:
        """查看指定 Shell 会话的输出内容。"""
        result = await sandbox.read_shell_output(session_id)
        return result.to_tool_content()

    return LangChainToolKit(name="shell", tools=[shell_execute, shell_read_output])
