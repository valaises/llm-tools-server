from typing import List, Iterator

from core.globals import MESSAGES_TOK_LIMIT
from core.chat_models import (
    ChatMessage,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageAssistant,
    ToolCall
)


def count_tokens(message: ChatMessage) -> int:
    return int(max(1, len(str(message.content))) / 4.)


def limit_messages(messages: List[ChatMessage]) -> List[ChatMessage]:
    new_messages = []

    take_messages = [
        isinstance(m, ChatMessageSystem) for m in messages
    ]
    tok_count = sum([
        count_tokens(m) for (m, take) in zip(messages, take_messages) if take
    ])

    take_messages.reverse()
    messages.reverse()

    for (message, take) in zip(messages, take_messages):
        if take == True:
            new_messages.append(message)
            continue

        m_tokens = count_tokens(message)
        if tok_count + m_tokens > MESSAGES_TOK_LIMIT:
            break

        tok_count += m_tokens
        new_messages.append(message)

    new_messages.reverse()

    return new_messages


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


def remove_trail_tool_calls(messages: List[ChatMessage]):
    # Get all unanswered tool calls
    unanswered_tool_calls = list(get_unanswered_tool_calls(messages))
    unanswered_tool_call_ids = {tool_call.id for tool_call in unanswered_tool_calls}

    # Remove unanswered tool calls from assistant messages
    for m in messages:
        if isinstance(m, ChatMessageAssistant) and m.tool_calls:
            m.tool_calls = [
                tool_call for tool_call in m.tool_calls
                if tool_call.id not in unanswered_tool_call_ids
            ]
            if len(m.tool_calls) == 0:
                m.tool_calls = None
