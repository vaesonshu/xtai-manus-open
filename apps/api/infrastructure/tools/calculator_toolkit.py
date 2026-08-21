"""计算器工具集：安全求值数学表达式。"""

from __future__ import annotations

import ast
import operator
from typing import Any

from langchain_core.tools import tool

from infrastructure.tools.langchain_toolkit import LangChainToolKit

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> int | float:
    """只允许数字常量与四则运算，避免执行任意 Python。"""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _BIN_OPS[type(node.op)](left, right)
    raise ValueError("不安全或无效的表达式")


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@tool
def calculate(expression: str) -> str:
    """安全计算数学表达式。支持 + - * / // % ** 与括号。涉及运算时必须调用本工具，禁止心算。"""
    text = expression.strip()
    if not text:
        raise ValueError("表达式不能为空")
    tree = ast.parse(text, mode="eval")
    return _format_number(_eval_node(tree))


def build_calculator_toolkit() -> LangChainToolKit:
    """构建计算器工具集。"""
    return LangChainToolKit(name="calculator", tools=[calculate])
