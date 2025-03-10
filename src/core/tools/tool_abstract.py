from typing import List

from core.chat_models import ChatTool, ChatMessageAny, ToolCall


class Tool:
    @property
    def name(self) -> str:
        """
        Get the unique identifier name of the tool.

        Returns:
            str: The name of the tool that uniquely identifies it in the system.

        Raises:
            NotImplementedError: This is an abstract property that must be implemented by concrete tool classes.
        """
        raise NotImplementedError("property 'name' is not implemented for tool")

    def validate_tool_call(self, tool_call: ToolCall) -> (bool, List[ChatMessageAny]):
        """
        Validate that the provided tool call is compatible with this tool.

        This method should verify that the provided ToolCall instance matches the expected
        interface of the tool, including checking parameter types, required fields,
        and any other tool-specific validation rules.

        Args:
            tool_call (ToolCall): The tool call to validate, containing function
                                 details and parameters.

        Returns:
            tuple: A pair containing:
                - bool: Indicates whether the validation was successful (True) or failed (False)
                - List[ChatMessageAny]: List of chat messages containing validation results or error details.
                                       They will help model correct itself and execute tool correctly.
                  Messages can be of type ChatMessage, ChatMessageSystem, ChatMessageUser,
                  ChatMessageAssistant, or ChatMessageTool.

        Raises:
            NotImplementedError: This is an abstract method that must be implemented by concrete tool classes.
        """
        raise NotImplementedError(f"method 'validate_tool_call' is not implemented for tool {self.name}")

    def execute(self, tool_call: ToolCall) -> (bool, List[ChatMessageAny]):
        """
        Execute the tool with the provided tool call and return execution results.

        Args:
            tool_call (ToolCall): The tool call containing function details and parameters
                                 to be executed. Includes function name and parameter
                                 values for this specific execution.

        Returns:
            tuple: A pair containing:
                - bool: Success status of the execution
                - List[ChatMessageAny]: List of chat messages generated during tool execution.
                  Messages can be of type ChatMessage, ChatMessageSystem, ChatMessageUser,
                  ChatMessageAssistant, or ChatMessageTool.

        Raises:
            NotImplementedError: This is an abstract method that must be implemented by concrete tool classes.
        """
        raise NotImplementedError(f"method 'execute' is not implemented for tool {self.name}")

    def as_chat_tool(self) -> ChatTool:
        """
        Convert the tool instance into a ChatTool configuration object.

        This method should create a ChatTool instance that describes the tool's interface,
        including its function name, description, and parameter specifications. This configuration
        is used by the chat system to understand how to interact with the tool.

        Returns:
            ChatTool: A configuration object containing the tool's type, function details,
                     and parameter specifications.

        Raises:
            NotImplementedError: This is an abstract method that must be implemented by concrete tool classes.
        """
        raise NotImplementedError(f"method 'as_chat_tool' is not implemented for tool {self.name}")
