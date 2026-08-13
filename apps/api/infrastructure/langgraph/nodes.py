"""LangGraph 节点：规划 / 执行 / 反思三阶段。

每个节点接收 ``AgentState`` 并返回增量状态（LangGraph 会按累加器合并）。
这里是 Manus 类自主 agent 的最小可用循环骨架，后续可接入工具调用、记忆等。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from infrastructure.langgraph.state import AgentState

PLANNER_SYSTEM = (
    "你是一个自主任务规划器。请将用户目标分解为清晰、可执行的步骤，"
    "用简洁的列表输出计划。"
)

EXECUTOR_SYSTEM = (
    "你是一个自主任务执行器。请基于已制定的计划执行当前步骤，"
    "并输出阶段性结果。"
)

REFLECTOR_SYSTEM = (
    "你是一个反思器。请评估当前进展是否已完成用户目标；"
    "若已完成，输出一行以 'DONE:' 开头、后跟最终结论；否则说明下一步。"
)


def planner_node(state: AgentState) -> dict:
    """规划节点：基于目标生成执行计划。"""
    goal = state.get("goal", "")
    plan = f"为「{goal}」制定的分步计划"
    return {
        "messages": [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=f"目标：{goal}"),
            AIMessage(content=f"[plan] {plan}"),
        ],
        "plan": plan,
        "iteration": state.get("iteration", 0),
    }


def executor_node(state: AgentState) -> dict:
    """执行节点：推进一步执行并产出阶段性结果。"""
    plan = state.get("plan", "")
    iteration = state.get("iteration", 0) + 1
    message = f"[execute] 第 {iteration} 步执行，依据计划：{plan}"
    return {
        "messages": [
            SystemMessage(content=EXECUTOR_SYSTEM),
            AIMessage(content=message),
        ],
        "iteration": iteration,
    }


def reflector_node(state: AgentState) -> dict:
    """反思节点：评估进展，若已完成则产出最终结果。"""
    iteration = state.get("iteration", 0)
    goal = state.get("goal", "")

    # 占位实现：达到最大迭代时视为完成；真实实现调用 LLM 判断。
    done = iteration >= state.get("max_iterations", 1)
    if done:
        result = {"goal": goal, "summary": f"已按计划完成「{goal}」"}
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
