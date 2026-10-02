"""The question-answering loop: ask the LLM, run the tools it calls, repeat until it answers."""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from opentelemetry.trace import Status, StatusCode
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.providers.base import LLMProvider, Message, ToolCall, ToolResult
from app.agent.tools import TOOLS, Tool, tool_specs
from app.cache import QueryCache, SessionStore
from app.observability import AGENT_LATENCY, AGENT_REQUESTS, LLM_CALLS, TOOL_CALLS, tracer

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You help hardware reliability engineers investigate drive-fleet test data: daily SMART \
telemetry per drive and failure-probability scores from a prediction model.

Answer only from the results of the tools you call; if the data does not answer the \
question, say so. Cite drive serial numbers, models and values from the results. Keep \
answers short and factual."""


class AgentError(RuntimeError):
    pass


@dataclass
class ToolInvocation:
    tool: str
    arguments: dict[str, Any]
    rows: list[dict[str, Any]] = field(default_factory=list)
    cached: bool = False
    error: str | None = None


@dataclass
class AgentAnswer:
    session_id: str
    answer: str
    tool_calls: list[ToolInvocation]


class Agent:
    def __init__(
        self,
        provider: LLMProvider,
        sessionmaker: async_sessionmaker[AsyncSession],
        query_cache: QueryCache,
        session_store: SessionStore,
        max_steps: int,
    ) -> None:
        self._provider = provider
        self._sessionmaker = sessionmaker
        self._cache = query_cache
        self._sessions = session_store
        self._max_steps = max_steps

    async def ask(self, question: str, session_id: str | None = None) -> AgentAnswer:
        session_id = session_id or uuid.uuid4().hex
        provider = self._provider.name
        store_key = f"{provider}:{session_id}"
        started = time.perf_counter()
        with tracer.start_as_current_span("agent.ask") as span:
            span.set_attribute("testlens.session_id", session_id)
            span.set_attribute("testlens.llm_provider", provider)
            try:
                answer = await self._run(question, session_id, store_key)
            except Exception as exc:
                AGENT_REQUESTS.labels(provider, "error").inc()
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                AGENT_LATENCY.labels(provider).observe(time.perf_counter() - started)
            AGENT_REQUESTS.labels(provider, "ok").inc()
            log.info(
                "agent.answered",
                session_id=session_id,
                tool_calls=[c.tool for c in answer.tool_calls],
            )
            return answer

    async def _run(self, question: str, session_id: str, store_key: str) -> AgentAnswer:
        transcript: list[Message] = await self._sessions.load(store_key)
        transcript.append(self._provider.user_message(question))
        invocations: list[ToolInvocation] = []
        specs = tool_specs()

        for step in range(self._max_steps):
            with tracer.start_as_current_span("agent.llm_call") as span:
                span.set_attribute("testlens.step", step)
                try:
                    turn = await self._provider.complete(SYSTEM_PROMPT, transcript, specs)
                except Exception:
                    LLM_CALLS.labels(self._provider.name, "error").inc()
                    raise
                LLM_CALLS.labels(self._provider.name, "ok").inc()
            transcript.append(turn.assistant_message)

            if not turn.tool_calls:
                await self._sessions.save(store_key, transcript)
                return AgentAnswer(session_id, turn.text, invocations)

            outcomes = await asyncio.gather(*(self._call_tool(c) for c in turn.tool_calls))
            invocations.extend(inv for inv, _ in outcomes)
            transcript.append(self._provider.tool_results_message([res for _, res in outcomes]))

        raise AgentError(f"No answer within {self._max_steps} steps")

    async def _call_tool(self, call: ToolCall) -> tuple[ToolInvocation, ToolResult]:
        with tracer.start_as_current_span("agent.tool_call") as span:
            span.set_attribute("testlens.tool", call.name)
            invocation = ToolInvocation(tool=call.name, arguments=call.arguments)
            tool = TOOLS.get(call.name)
            try:
                if tool is None:
                    raise ValueError(f"Unknown tool {call.name!r}")
                args = tool.args_model.model_validate(call.arguments).model_dump()
                invocation.arguments = args
                invocation.rows, invocation.cached = await self._cache.get_or_compute(
                    call.name, args, lambda: self._query(tool, args)
                )
            except (ValueError, ValidationError) as exc:
                invocation.error = str(exc)
                span.set_status(Status(StatusCode.ERROR, invocation.error))
                TOOL_CALLS.labels(call.name, "none", "invalid").inc()
                return invocation, ToolResult(call.id, invocation.error, is_error=True)

            cache = "hit" if invocation.cached else "miss"
            span.set_attribute("testlens.cache", cache)
            span.set_attribute("testlens.rows", len(invocation.rows))
            TOOL_CALLS.labels(call.name, cache, "ok").inc()
            return invocation, ToolResult(call.id, json.dumps(invocation.rows))

    async def _query(self, tool: Tool, args: dict[str, Any]) -> list[dict[str, Any]]:
        # One DB session per tool call so parallel calls never share a connection.
        async with self._sessionmaker() as session:
            return await tool.run(session, **args)
