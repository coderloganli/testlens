"""Provider-neutral interface the agent loop talks to.

Each provider owns its transcript format: messages are opaque JSON-serialisable
dicts that the agent appends in order and persists between turns, so a provider
can carry native content (for example reasoning blocks) back to its API unchanged.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

Message = dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass
class LLMTurn:
    assistant_message: Message
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMError(RuntimeError):
    """The provider could not produce a usable turn (refusal, truncation, API failure)."""


class LLMProvider(Protocol):
    name: str

    def user_message(self, text: str) -> Message: ...

    def tool_results_message(self, results: list[ToolResult]) -> Message: ...

    async def complete(
        self, system: str, transcript: list[Message], tools: list[ToolSpec]
    ) -> LLMTurn: ...
