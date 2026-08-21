"""SSE 流式事件 Pydantic Schema：Presentation 层出站契约校验。"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

# --- 各事件类型 Schema（与 domain/event 序列化字段对齐）---


class _StreamEventBase(BaseModel):
    """流式事件公共字段。"""

    id: str
    created_at: str


class PlanStreamEventSchema(_StreamEventBase):
    type: Literal["plan"]
    plan: dict[str, Any]
    status: str


class StepStreamEventSchema(_StreamEventBase):
    type: Literal["step"]
    step: dict[str, Any]
    status: str


class FileAttachmentSchema(BaseModel):
    """文件附件 schema，与 domain/file/attachment.py 序列化字段对齐。"""

    id: str = ""
    filename: str = ""
    filepath: str = ""
    key: str = ""
    extension: str = ""
    mime_type: str = ""
    size: int = 0


class MessageStreamEventSchema(_StreamEventBase):
    type: Literal["message"]
    role: Literal["user", "assistant"]
    message: str = ""
    attachments: list[FileAttachmentSchema] = Field(default_factory=list)
    partial: bool = False
    stream_id: str | None = None


class ToolStreamEventSchema(_StreamEventBase):
    type: Literal["tool"]
    step_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    function_name: str = ""
    function_args: dict[str, Any] = Field(default_factory=dict)
    function_result: Any = None
    status: str
    tool_content: dict[str, Any] | None = None


class TitleStreamEventSchema(_StreamEventBase):
    type: Literal["title"]
    title: str = ""


class WaitStreamEventSchema(_StreamEventBase):
    type: Literal["wait"]
    reason: str = ""
    question: str = ""


class ErrorStreamEventSchema(_StreamEventBase):
    type: Literal["error"]
    error: str = ""


class DoneStreamEventSchema(_StreamEventBase):
    type: Literal["done"]


StreamEventPayload = Annotated[
    Union[
        PlanStreamEventSchema,
        StepStreamEventSchema,
        MessageStreamEventSchema,
        ToolStreamEventSchema,
        TitleStreamEventSchema,
        WaitStreamEventSchema,
        ErrorStreamEventSchema,
        DoneStreamEventSchema,
    ],
    Field(discriminator="type"),
]

_stream_event_adapter: TypeAdapter[StreamEventPayload] = TypeAdapter(StreamEventPayload)


def validate_stream_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化 SSE 事件载荷；非法事件在边界层拦截。"""
    validated = _stream_event_adapter.validate_python(payload)
    result = validated.model_dump(mode="json", exclude_none=True)
    # 空 step_id 会被 exclude_none 保留为空串；前端依赖该字段挂到步骤下
    if payload.get("type") == "tool" and payload.get("step_id"):
        result["step_id"] = str(payload["step_id"])
    return result
