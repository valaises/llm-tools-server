from typing import Any

from openai_wrappers.types import ToolCall, ChatMessageTool


def build_tool_call(content: Any, tool_call: ToolCall) -> ChatMessageTool:
    return ChatMessageTool(
        role="tool",
        content=content,
        tool_call_id=tool_call.id
    )
