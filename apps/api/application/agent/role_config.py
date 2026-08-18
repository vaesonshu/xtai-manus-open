"""按 Agent 角色区分的 prompt 与工具配置。"""

from __future__ import annotations

from dataclasses import dataclass

from application.prompts import GLOBAL_SYSTEM_PROMPT, JSON_RESPONSE_FORMAT, REACT_SYSTEM_PROMPT
from domain.agent.role import AgentRole

# 全局身份 + ReAct 执行规则 + 角色后缀
_BASE_SYSTEM = f"{GLOBAL_SYSTEM_PROMPT.strip()}\n\n{REACT_SYSTEM_PROMPT.strip()}\n\n"

_INTERACTION_TOOLS = ("message_notify_user", "message_ask_user")
_RESEARCHER_TOOLS = _INTERACTION_TOOLS + (
    "search_web",
    "read_file",
    "find_files",
    "browser_view",
    "browser_navigate",
)
_CODER_TOOLS = _INTERACTION_TOOLS + (
    "read_file",
    "write_file",
    "replace_in_file",
    "search_in_file",
    "find_files",
    "shell_execute",
    "shell_read_output",
)
_EXECUTOR_TOOLS = _CODER_TOOLS + ("search_web", "echo")


@dataclass(frozen=True)
class RoleConfig:
    """单个角色的执行配置。"""

    system_prompt: str
    tool_names: tuple[str, ...] = ()
    response_format: dict | None = None
    tool_choice: str | None = None


ROLE_CONFIG: dict[AgentRole, RoleConfig] = {
    AgentRole.RESEARCHER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你擅长信息收集与调研，优先使用搜索与文件工具。",
        tool_names=_RESEARCHER_TOOLS,
        response_format=JSON_RESPONSE_FORMAT,
    ),
    AgentRole.CODER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你擅长整理方案与生成可交付内容，可使用文件与 Shell 工具。",
        tool_names=_CODER_TOOLS,
        response_format=JSON_RESPONSE_FORMAT,
    ),
    AgentRole.REVIEWER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你负责复核质量与完整性，输出简明结论。",
        tool_names=_INTERACTION_TOOLS,
        response_format=JSON_RESPONSE_FORMAT,
        tool_choice="none",
    ),
    AgentRole.EXECUTOR: RoleConfig(
        system_prompt=_BASE_SYSTEM,
        tool_names=_EXECUTOR_TOOLS,
        response_format=JSON_RESPONSE_FORMAT,
    ),
    AgentRole.COORDINATOR: RoleConfig(
        system_prompt=_BASE_SYSTEM,
        tool_names=_INTERACTION_TOOLS,
        response_format=JSON_RESPONSE_FORMAT,
        tool_choice="none",
    ),
    AgentRole.PLANNER: RoleConfig(
        system_prompt="你是规划智能体，规划由独立服务完成。",
        tool_names=(),
        tool_choice="none",
    ),
}


def get_role_config(role: AgentRole) -> RoleConfig:
    """获取角色配置，未知角色回落为 EXECUTOR。"""
    return ROLE_CONFIG.get(role, ROLE_CONFIG[AgentRole.EXECUTOR])
