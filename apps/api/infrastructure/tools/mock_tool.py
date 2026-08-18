"""Mock 工具集：用于验证 ReAct 循环与事件流。"""

from __future__ import annotations

from typing import Any

from domain.tool.result import ToolResult


class MockToolKit:
    """提供 ``echo`` 工具，将输入文本原样返回。"""

    name = "mock"

    def get_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "回显输入文本，用于测试工具调用链路",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "需要回显的文本",
                            }
                        },
                        "required": ["text"],
                    },
                },
            }
        ]

    def has_tool(self, function_name: str) -> bool:
        return function_name == "echo"

    async def invoke(self, function_name: str, arguments: dict[str, Any]) -> ToolResult:
        if function_name != "echo":
            return ToolResult(success=False, message=f"未知工具: {function_name}")
        text = str(arguments.get("text", "")).strip()
        return ToolResult(success=True, message=text or "(empty)", data={"text": text})
