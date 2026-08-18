"""多 Agent 规划 LLM 输出结构。"""

from __future__ import annotations

PLAN_RESPONSE_FORMAT: dict = {
    "type": "json_schema",
    "json_schema": {
        "name": "multi_agent_plan",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "message": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent_role": {
                                "type": "string",
                                "enum": [
                                    "coordinator",
                                    "planner",
                                    "researcher",
                                    "coder",
                                    "reviewer",
                                    "executor",
                                ],
                            },
                            "description": {"type": "string"},
                        },
                        "required": ["agent_role", "description"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "message", "steps"],
            "additionalProperties": False,
        },
    },
}

PLANNER_SYSTEM_PROMPT = """你是一个多 Agent 任务规划器。
请将用户目标拆解为 2-5 个可执行步骤，并为每步指定最合适的 agent_role：
- researcher：信息收集、调研
- coder：代码实现、数据处理
- reviewer：质量复核、风险检查
- executor：通用执行
- coordinator：协调与汇总

输出 JSON，steps 按执行顺序排列。"""

REPLANNER_SYSTEM_PROMPT = """你是一个多 Agent 重规划器。
根据当前目标、历史记忆与重规划原因，生成新的步骤列表（跳过已完成部分）。
保持步骤具体、可执行，并合理分配 agent_role。"""
