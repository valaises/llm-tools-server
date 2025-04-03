from typing import List, Dict, Any, Optional

from core.tools.tool_utils import build_tool_call
from openai_wrappers.types import (
    ChatTool, ChatToolFunction, ChatToolParameters,
    ChatToolParameterProperty, ToolCall, ChatMessage
)
from chat_tools.tool_usage import Tool, ToolProps


class ToolPingPong(Tool):
    @property
    def name(self) -> str:
        return "ping_pong"

    def validate_tool_call_args(self, ctx: Any, tool_call: ToolCall, args: Dict[str, Any]) -> (bool, List[ChatMessage]):
        message = args.get("message")

        if not isinstance(message, str):
            return False, [build_tool_call(f"Error: Expected type message str, got '{type(message)}'", tool_call)]

        if message != "ping":
            return False, [build_tool_call(f"Error: Expected message 'ping', got '{message}'", tool_call)]

        return True, []

    async def execute(self, ctx: Optional[Any], tool_call: ToolCall, args: Dict[str, Any]) -> (bool, List[ChatMessage]):
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

    def props(self) -> ToolProps:
        return ToolProps(
            tool_name=self.name,
            depends_on=[]
        )
