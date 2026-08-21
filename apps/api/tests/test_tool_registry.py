"""ToolRegistry schema 过滤测试。"""

from __future__ import annotations

from infrastructure.tools import (
    ToolRegistry,
    build_calculator_toolkit,
    build_interaction_toolkit,
    build_mock_toolkit,
    build_time_toolkit,
)


def test_get_schemas_filters_by_function_name() -> None:
    """role_config.tool_names 存的是 function 名，不能用工具集名去匹配。"""
    registry = ToolRegistry(
        [
            build_mock_toolkit(),
            build_interaction_toolkit(),
            build_calculator_toolkit(),
            build_time_toolkit(),
        ]
    )

    schemas = registry.get_schemas(
        ("echo", "message_notify_user", "calculate", "get_current_time")
    )

    names = sorted(schema["function"]["name"] for schema in schemas)
    assert names == [
        "calculate",
        "echo",
        "get_current_time",
        "message_notify_user",
    ]


def test_get_schemas_ignores_unknown_function_names() -> None:
    registry = ToolRegistry([build_mock_toolkit()])

    schemas = registry.get_schemas(("does_not_exist",))

    assert schemas == []
