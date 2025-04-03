from typing import List

from openai_wrappers.types import ChatMessage, ChatMessageContentItemDocSearch, ChatMessageContentItemText


def convert_messages_for_openai_format(messages: List[ChatMessage]) -> List[ChatMessage]:
    """
    Converts a list of ChatMessage objects to be compatible with OpenAI's API format.

    For each message with non-string content, this function processes content items
    and ensures that ChatMessageContentItemDocSearch items are properly formatted
    by adding a text version before the doc search item itself.

    Args:
        messages: A list of ChatMessage objects to be converted

    Returns:
        A new list of ChatMessage objects formatted for OpenAI's API
    """
    result = []
    for message in messages:
        new_message = message.model_copy()
        if not isinstance(message.content, str):
            new_content = []
            for c in message.content:
                if isinstance(c, ChatMessageContentItemDocSearch):
                    new_content.append(ChatMessageContentItemText(
                        text=c.text,
                        type="text"
                    ))
                else:
                    new_content.append(c)
            new_message.content = new_content
        result.append(new_message)
    return result
