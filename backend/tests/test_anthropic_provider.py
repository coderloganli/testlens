"""AnthropicProvider request/response mapping, exercised against a stub client (no network)."""

from types import SimpleNamespace

import pytest

from app.agent.providers.anthropic_provider import FALLBACK_BETA, AnthropicProvider
from app.agent.providers.base import LLMError, ToolResult, ToolSpec


class Block(SimpleNamespace):
    def model_dump(self, **_):
        return dict(vars(self))


class StubMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def provider_with(response):
    messages = StubMessages(response)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicProvider("model-x", "medium", 1024, client=client), messages


async def test_maps_tool_use_blocks_and_request_parameters():
    response = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            Block(type="text", text="Checking."),
            Block(type="tool_use", id="tu_1", name="fleet_summary", input={}),
        ],
    )
    provider, messages = provider_with(response)
    spec = ToolSpec("fleet_summary", "desc", {"type": "object", "properties": {}})

    turn = await provider.complete("sys", [provider.user_message("q")], [spec])

    assert turn.text == "Checking."
    assert [(c.id, c.name) for c in turn.tool_calls] == [("tu_1", "fleet_summary")]
    assert turn.assistant_message["content"][1]["type"] == "tool_use"
    assert messages.kwargs["model"] == "model-x"
    assert messages.kwargs["tools"][0]["input_schema"] == spec.input_schema
    assert messages.kwargs["betas"] == [FALLBACK_BETA]


async def test_refusal_raises():
    provider, _ = provider_with(SimpleNamespace(stop_reason="refusal", content=[]))
    with pytest.raises(LLMError):
        await provider.complete("sys", [provider.user_message("q")], [])


def test_tool_results_are_sent_in_one_user_message():
    provider, _ = provider_with(None)
    message = provider.tool_results_message(
        [ToolResult("a", "[]"), ToolResult("b", "bad", is_error=True)]
    )
    assert message["role"] == "user"
    assert [b["tool_use_id"] for b in message["content"]] == ["a", "b"]
    assert message["content"][1]["is_error"] is True
