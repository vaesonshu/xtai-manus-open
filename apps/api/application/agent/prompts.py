"""Agent 执行阶段提示词。"""

from __future__ import annotations

EXECUTION_PROMPT = """请完成以下步骤：

步骤描述：{step_description}
执行角色：{agent_role}

请输出该步骤的执行结果，简明扼要。"""
