import json

from typing import List, Dict, Any

from core.chat_models import (
    ChatTool,
    ChatToolFunction,
    ChatToolParameters,
    ChatToolParameterProperty,
    ToolCall,
    ChatMessage
)

from .tool_abstract import Tool, build_tool_call


class ToolPingPong(Tool):
    @property
    def name(self) -> str:
        return "ping_pong"

    def validate_tool_call_args(self, tool_call: ToolCall, args: Dict[str, Any]) -> (bool, List[ChatMessage]):
        message = args.get("message")

        if not isinstance(message, str):
            return False, [build_tool_call(f"Error: Expected type message str, got '{type(message)}'", tool_call)]

        if message != "ping":
            return False, [build_tool_call(f"Error: Expected message 'ping', got '{message}'", tool_call)]

        return True, []

    def execute(self, tool_call: ToolCall, _args: Dict[str, Any]) -> (bool, List[ChatMessage]):
        return True, [build_tool_call("pong", tool_call)]

    def as_chat_tool(self) -> ChatTool:
        return ChatTool(
            type="function",
            function=ChatToolFunction(
                name="ping_pong",
                description="A simple ping-pong function that responds with 'pong' when called with 'ping'.",
                parameters=ChatToolParameters(
                    type="object",
                    properties={
                        "message": ChatToolParameterProperty(
                            type="string",
                            description="The message to send (should be 'ping')",
                            enum=["ping"]
                        )
                    },
                    required=["message"]
                )
            )
        )
