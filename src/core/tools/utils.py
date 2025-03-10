from core.chat_models import ToolCall, ChatMessageTool


def build_tool_call(content: str, tool_call: ToolCall) -> ChatMessageTool:
    return ChatMessageTool(
        role="tool",
        content=content,
        tool_call_id=tool_call.id
    )
