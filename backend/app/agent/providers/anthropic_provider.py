"""Claude via the official Anthropic Python SDK (Messages API with client tools)."""

import anthropic

from app.agent.providers.base import (
    LLMError,
    LLMTurn,
    Message,
    ToolCall,
    ToolResult,
    ToolSpec,
)

# Server-side refusal fallback: the API re-runs a declined request on a
# fallback model it selects by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        model: str,
        effort: str,
        max_tokens: int,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        # The zero-arg client resolves credentials from the environment (ANTHROPIC_API_KEY, ...).
        self._client = client or anthropic.AsyncAnthropic()
        self._model = model
        self._effort = effort
        self._max_tokens = max_tokens

    def user_message(self, text: str) -> Message:
        return {"role": "user", "content": text}

    def tool_results_message(self, results: list[ToolResult]) -> Message:
        # All results for one assistant turn go back in a single user message.
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": r.call_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in results
            ],
        }

    async def complete(
        self, system: str, transcript: list[Message], tools: list[ToolSpec]
    ) -> LLMTurn:
        try:
            response = await self._client.beta.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=transcript,
                tools=[
                    {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                    for t in tools
                ],
                output_config={"effort": self._effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise LLMError("Anthropic rate limit reached") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the Anthropic API") from exc

        if response.stop_reason == "refusal":
            raise LLMError("The model declined to answer this question")
        if response.stop_reason == "max_tokens":
            raise LLMError("The model response was truncated")

        # Echo the full content (including thinking/fallback blocks) back on later turns.
        assistant = {
            "role": "assistant",
            "content": [b.model_dump(mode="json", exclude_none=True) for b in response.content],
        }
        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [
            ToolCall(id=b.id, name=b.name, arguments=dict(b.input))
            for b in response.content
            if b.type == "tool_use"
        ]
        return LLMTurn(assistant_message=assistant, text=text, tool_calls=calls)
