"""Deterministic provider for tests and offline development.

It picks one tool from keywords in the latest question, then answers from that
tool's result. No network, no randomness.
"""

import json
import re

from app.agent.providers.base import LLMTurn, Message, ToolCall, ToolResult, ToolSpec

SERIAL_PATTERN = re.compile(r"\b[A-Z0-9]{4}-\d{4}\b")


class FakeProvider:
    name = "fake"

    def user_message(self, text: str) -> Message:
        return {"role": "user", "content": text}

    def tool_results_message(self, results: list[ToolResult]) -> Message:
        return {
            "role": "tool",
            "results": [
                {"call_id": r.call_id, "content": r.content, "is_error": r.is_error}
                for r in results
            ],
        }

    async def complete(
        self, system: str, transcript: list[Message], tools: list[ToolSpec]
    ) -> LLMTurn:
        last = transcript[-1]
        if last["role"] == "user":
            call = self._plan(last["content"], len(transcript), {t.name for t in tools})
            message = {"role": "assistant", "content": "", "tool_calls": [call.__dict__]}
            return LLMTurn(assistant_message=message, text="", tool_calls=[call])

        result = last["results"][0]
        if result["is_error"]:
            text = f"The query failed: {result['content']}"
        else:
            rows = json.loads(result["content"])
            text = self._summarise(rows)
        return LLMTurn(assistant_message={"role": "assistant", "content": text}, text=text)

    @staticmethod
    def _plan(question: str, turn: int, available: set[str]) -> ToolCall:
        call_id = f"call_{turn}"
        serial = SERIAL_PATTERN.search(question.upper())
        if serial and "smart_history" in available:
            return ToolCall(call_id, "smart_history", {"serial_number": serial.group(0)})
        if re.search(r"\b(fleet|models?|summary)\b", question, re.IGNORECASE):
            return ToolCall(call_id, "fleet_summary", {})
        return ToolCall(call_id, "top_risk_drives", {"limit": 5})

    @staticmethod
    def _summarise(rows: list[dict]) -> str:
        if not rows:
            return "The query returned no matching rows."
        first = rows[0]
        if "failure_probability" in first:
            return (
                f"{len(rows)} drives returned; the highest-risk drive is {first['serial_number']} "
                f"({first['model']}) with failure probability {first['failure_probability']}."
            )
        if "drive_count" in first:
            total = sum(r["drive_count"] for r in rows)
            return f"The fleet has {total} drives across {len(rows)} models."
        latest = rows[-1]
        return (
            f"{len(rows)} daily readings returned; on {latest['observed_on']} the drive had "
            f"{latest['reallocated_sectors']} reallocated and {latest['pending_sectors']} "
            "pending sectors."
        )
