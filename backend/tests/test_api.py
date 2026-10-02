import pytest

from app.agent.providers.base import LLMTurn, ToolCall
from app.agent.providers.fake import FakeProvider
from app.seed import build_sample


async def test_health_and_readiness(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    assert (await client.get("/readyz")).json() == {"status": "ready"}


async def test_ask_returns_answer_with_query_results(client):
    response = await client.post("/api/ask", json={"question": "Which drives are most at risk?"})
    assert response.status_code == 200
    body = response.json()

    [call] = body["tool_calls"]
    assert call["tool"] == "top_risk_drives"
    assert call["cached"] is False
    assert len(call["rows"]) == 5
    assert call["rows"][0]["serial_number"] in body["answer"]


async def test_smart_history_question(client):
    serial = build_sample()[0][0].serial_number
    response = await client.post("/api/ask", json={"question": f"Show SMART trend for {serial}"})
    [call] = response.json()["tool_calls"]
    assert call["tool"] == "smart_history"
    assert call["arguments"]["serial_number"] == serial
    assert call["rows"]


async def test_repeat_query_is_served_from_cache(client):
    question = {"question": "Give me a fleet summary"}
    first = (await client.post("/api/ask", json=question)).json()
    second = (await client.post("/api/ask", json=question)).json()
    assert first["tool_calls"][0]["cached"] is False
    assert second["tool_calls"][0]["cached"] is True
    assert first["tool_calls"][0]["rows"] == second["tool_calls"][0]["rows"]


async def test_session_transcript_persists_across_questions(client, redis):
    first = (await client.post("/api/ask", json={"question": "fleet summary"})).json()
    session_id = first["session_id"]
    await client.post(
        "/api/ask", json={"question": "Which drives are at risk?", "session_id": session_id}
    )
    transcript = await redis.get(f"testlens:session:fake:{session_id}")
    assert transcript.count('"role": "user"') == 2


async def test_rejects_empty_question(client):
    assert (await client.post("/api/ask", json={"question": ""})).status_code == 422


async def test_metrics_endpoint_exposes_agent_counters(client):
    await client.post("/api/ask", json={"question": "fleet summary"})
    metrics = (await client.get("/metrics/")).text
    assert "testlens_agent_requests_total" in metrics
    assert "testlens_agent_tool_calls_total" in metrics


class InvalidArgumentsProvider(FakeProvider):
    """Calls a tool with arguments that fail validation, then answers."""

    async def complete(self, system, transcript, tools):
        if transcript[-1]["role"] == "user":
            call = ToolCall("call_1", "top_risk_drives", {"limit": 0})
            return LLMTurn({"role": "assistant", "tool_calls": [call.__dict__]}, "", [call])
        return await super().complete(system, transcript, tools)


@pytest.mark.parametrize("provider", [InvalidArgumentsProvider()])
async def test_invalid_tool_arguments_are_reported_to_the_model(client):
    body = (await client.post("/api/ask", json={"question": "anything"})).json()
    [call] = body["tool_calls"]
    assert call["error"] and call["rows"] == []
    assert body["answer"].startswith("The query failed")
