from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, confloat, conint


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, List[Any]]


class ChatMessageSystem(ChatMessage):
    role: Literal["system", "developer"]
    name: Optional[str] = None


class ChatMessageUser(ChatMessage):
    role: Literal["user"]
    name: Optional[str] = None


class ChatMessageAssistant(ChatMessage):
    role: Literal["assistant"]
    refusal: Optional[str] = None
    name: Optional[str] = None
    audio: Optional[Any] = None
    tool_calls: Optional[List[Dict]] = None


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: Literal["function"]
    function:ToolCallFunction


class ChatMessageToolCall(ChatMessage):
    role: Literal["tool"]
    tool_call_id: Optional[str] = None


class ChatFunctionParameter(BaseModel):
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None


class ChatFunctionParameters(BaseModel):
    type: Literal["object"] = "object"
    properties: dict[str, ChatFunctionParameter]
    required: Optional[List[str]] = None


class ChatFunction(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: ChatFunctionParameters


def default_modalities() -> List[str]:
    return ["text"]


class ChatPost(BaseModel):
    # Required fields
    model: str
    messages: List[Union[ChatMessageSystem, ChatMessageUser, ChatMessageAssistant, ChatMessageToolCall]]

    # Optional fields with defaults
    temperature: Optional[confloat(ge=0, le=2)] = Field(default=1)
    top_p: Optional[confloat(ge=0, le=1)] = Field(default=1)
    n: Optional[conint(ge=1)] = Field(default=1)
    stream: Optional[bool] = Field(default=False)
    presence_penalty: Optional[confloat(ge=-2, le=2)] = Field(default=0)
    frequency_penalty: Optional[confloat(ge=-2, le=2)] = Field(default=0)

    # Optional fields without defaults
    stop: Optional[Union[str, List[str]]] = None
    logit_bias: Optional[dict[str, float]] = None
    user: Optional[str] = None

    # New fields
    store: Optional[bool] = Field(default=False)
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = Field(default="medium")
    metadata: Optional[dict[str, str]] = None
    logprobs: Optional[bool] = Field(default=False)
    top_logprobs: Optional[conint(ge=0, le=20)] = None
    max_completion_tokens: Optional[conint(ge=1)] = None
    modalities: Optional[List[str]] = Field(default_factory=default_modalities)
    prediction: Optional[dict] = None
    audio: Optional[dict] = None
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    service_tier: Optional[Literal["auto", "default"]] = Field(default="auto")
    stream_options: Optional[dict] = None
    tools: Optional[List[dict]] = None
    tool_choice: Optional[Union[str, dict]] = None
    parallel_tool_calls: Optional[bool] = Field(default=True)

    # Deprecated fields
    max_tokens: Optional[conint(ge=1)] = Field(default=None, deprecated=True)
    functions: Optional[List[ChatFunction]] = Field(default=None, deprecated=True)
    function_call: Optional[Union[str, dict]] = Field(default=None, deprecated=True)
