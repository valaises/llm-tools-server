from typing import List, Iterator

from openai_wrappers.types import (
    ChatMessage,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageAssistant,
    ToolCall
)


def get_unanswered_tool_calls(messages: List[ChatMessage]) -> Iterator[ToolCall]:
    # Get all tool call IDs from responses
    tool_messages: List[ChatMessageTool] = [
        m for m in messages if isinstance(m, ChatMessageTool)
    ]
    answered_tool_call_ids = {
        tool_call_id for m in tool_messages if (tool_call_id := m.tool_call_id)
    }

    # yield all unanswered tool calls
    for m in messages:
        if isinstance(m, ChatMessageAssistant) and m.tool_calls:
            for tool_call in m.tool_calls:
                if tool_call.id not in answered_tool_call_ids:
                    yield tool_call
