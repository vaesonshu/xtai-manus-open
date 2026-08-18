"""按 Agent 角色区分的 prompt 与工具配置。"""

from __future__ import annotations

from dataclasses import dataclass

from domain.agent.role import AgentRole

_BASE_SYSTEM = (
    "你是一个多 Agent 协作系统中的执行智能体。"
    "请根据当前步骤描述完成任务，必要时调用工具。"
)


@dataclass(frozen=True)
class RoleConfig:
    """单个角色的执行配置。"""

    system_prompt: str
    tool_names: tuple[str, ...] = ()
    response_format: dict | None = None
    tool_choice: str | None = None


ROLE_CONFIG: dict[AgentRole, RoleConfig] = {
    AgentRole.RESEARCHER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你擅长信息收集与调研，可使用 echo 工具验证流程。",
        tool_names=("echo", "message_ask_user"),
    ),
    AgentRole.CODER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你擅长整理方案与生成可交付内容。",
        tool_names=("echo", "message_ask_user"),
    ),
    AgentRole.REVIEWER: RoleConfig(
        system_prompt=_BASE_SYSTEM + "你负责复核质量与完整性，输出简明结论。",
        tool_names=(),
        tool_choice="none",
    ),
    AgentRole.EXECUTOR: RoleConfig(
        system_prompt=_BASE_SYSTEM,
        tool_names=("echo",),
    ),
    AgentRole.COORDINATOR: RoleConfig(
        system_prompt=_BASE_SYSTEM,
        tool_names=(),
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
