import json
from typing import List

from .tool_abstract import Tool
from .tool_ping_pong import ToolPingPong
from .utils import build_tool_call
from ..chat import get_unanswered_tool_calls
from core.chat_models import (
    ChatMessageAny,
    ChatTool,
    ChatMessageUser,
    ChatMessageTool
)


TOOLS: List[Tool] = [
    ToolPingPong(),
]
assert len({t.name for t in TOOLS}) == len(TOOLS), "TOOLS: names must be unique"


def execute_tools_if_needed(messages: List[ChatMessageAny]) -> List[ChatMessageTool]:
    """Execute pending tool calls from the chat message history.

    This function processes chat messages to find and execute any unanswered tool calls.
    It works by:
    1. Finding the most recent sequence of messages since the last user message
    2. Identifying unanswered tool calls in those messages
    3. Executing each tool call if the tool exists and arguments are valid

    Args:
        messages (List[ChatMessageAny]): A list of chat messages to process

    Returns:
        List[ChatMessageTool]: A list of tool response messages. These can include:
            - Error messages for non-existent tools
            - Error messages for invalid JSON arguments
            - Validation error messages from tools
            - Actual tool execution results
    """

    # Collect messages since last user message
    messages_since_user = []
    for message in reversed(messages):
        if isinstance(message, ChatMessageUser):
            break
        messages_since_user.insert(0, message)

    tool_res_messages = []
    for tool_call in get_unanswered_tool_calls(messages_since_user):
        tool = [t for t in TOOLS if t.name == tool_call.function.name]
        if not tool:
            tool_res_messages.append(build_tool_call(
                f"Error: tool with name '{tool_call.function.name}' does not exist", tool_call
            ))
            continue

        tool = tool[0]

        # assuming, there's always JSON in arguments
        try:
            _ = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_res_messages.append(build_tool_call(
                f"Error: invalid JSON in arguments: {tool_call.function.arguments}", tool_call
            ))
            continue

        ok, msgs = tool.validate_tool_call(tool_call)
        tool_res_messages.extend(msgs)

        if not ok:
            continue

        _ok, msgs = tool.execute(tool_call)
        tool_res_messages.extend(msgs)

    return tool_res_messages



def get_tools_list() -> List[ChatTool]:
    """
    Get a list of all available tools in their ChatTool configuration format.

    This function converts all registered tools (from the TOOLS list) into their
    ChatTool representations by calling as_chat_tool() on each tool instance.
    The ChatTool format includes each tool's interface definition, such as its
    function name, description, and parameter specifications.

    Returns:
        List[ChatTool]: A list of ChatTool configurations for all available tools
            in the system. Each ChatTool object contains the tool's type, function
            details, and parameter specifications needed by the chat system to
            interact with the tool.
    """
    return [t.as_chat_tool() for t in TOOLS]
