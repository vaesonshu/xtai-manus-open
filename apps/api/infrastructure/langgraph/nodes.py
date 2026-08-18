"""LangGraph 节点：规划 / 执行 / 反思三阶段。

每个节点接收 ``AgentState`` 并返回增量状态（LangGraph 会按累加器合并）。
规划节点产出结构化多 Agent 步骤；执行节点按当前步骤角色推进。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from domain.agent.role import AgentRole
from infrastructure.langgraph.planning_bridge import build_offline_plan, plan_to_state_steps
from infrastructure.langgraph.state import AgentState

PLANNER_SYSTEM = (
    "你是一个多 Agent 任务规划器。请将用户目标分解为清晰、可执行的步骤，"
    "并为每步指定执行角色（researcher/coder/reviewer/executor）。"
)

EXECUTOR_SYSTEM = (
    "你是一个多 Agent 执行器。请基于当前步骤的角色与描述执行工作，"
    "并输出阶段性结果。"
)

REFLECTOR_SYSTEM = (
    "你是一个反思器。请评估当前进展是否已完成用户目标；"
    "若已完成，输出一行以 'DONE:' 开头、后跟最终结论；否则说明下一步。"
)


def planner_node(state: AgentState) -> dict:
    """规划节点：生成结构化多 Agent 步骤列表。"""
    goal = state.get("goal", "")
    memory_context = state.get("memory_context", "")

    # 离线降级：生产环境由 PlanningApplicationService + LLM 预先写入 state
    plan = build_offline_plan(goal)
    plan_steps = plan_to_state_steps(plan)
    plan_summary = " | ".join(
        f"[{step['agent_role']}] {step['description']}" for step in plan_steps
    )

    messages = [
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=f"目标：{goal}"),
    ]
    if memory_context:
        messages.append(HumanMessage(content=f"记忆上下文：\n{memory_context}"))
    messages.append(AIMessage(content=f"[plan] {plan_summary}"))

    return {
        "messages": messages,
        "plan": plan_summary,
        "plan_steps": plan_steps,
        "current_step_index": 0,
        "iteration": state.get("iteration", 0),
    }


def executor_node(state: AgentState) -> dict:
    """执行节点：按当前步骤的角色推进一步。"""
    plan_steps = state.get("plan_steps", [])
    step_index = state.get("current_step_index", 0)
    iteration = state.get("iteration", 0) + 1

    if step_index < len(plan_steps):
        current = plan_steps[step_index]
        role = AgentRole.from_value(str(current.get("agent_role", "")))
        description = str(current.get("description", ""))
        message = (
            f"[execute:{role.value}] 第 {step_index + 1} 步：{description}"
        )
        next_index = step_index + 1
    else:
        message = f"[execute] 第 {iteration} 步：计划步骤已耗尽，继续反思"
        next_index = step_index

    return {
        "messages": [
            SystemMessage(content=EXECUTOR_SYSTEM),
            AIMessage(content=message),
        ],
        "iteration": iteration,
        "current_step_index": next_index,
    }


def reflector_node(state: AgentState) -> dict:
    """反思节点：评估进展，若已完成则产出最终结果。"""
    iteration = state.get("iteration", 0)
    goal = state.get("goal", "")
    plan_steps = state.get("plan_steps", [])
    step_index = state.get("current_step_index", 0)
    all_steps_done = step_index >= len(plan_steps) and len(plan_steps) > 0

    done = all_steps_done or iteration >= state.get("max_iterations", 1)
    if done:
        result = {
            "goal": goal,
            "summary": f"已按多 Agent 计划完成「{goal}」",
            "steps_completed": step_index,
        }
        return {
            "messages": [AIMessage(content=f"DONE: {result['summary']}")],
            "reflection": result["summary"],
            "result": result,
        }
    return {
        "messages": [
            SystemMessage(content=REFLECTOR_SYSTEM),
            AIMessage(content="[reflect] 尚未完成，继续执行下一步。"),
        ],
        "reflection": "继续执行",
    }
