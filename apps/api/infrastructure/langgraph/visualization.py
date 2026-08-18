"""LangGraph 图结构导出（Mermaid）。"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph


def export_mermaid(graph: CompiledStateGraph) -> str:
    """导出 StateGraph 的 Mermaid 文本。"""
    return graph.get_graph().draw_mermaid()
