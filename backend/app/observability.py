"""Structured logging, OpenTelemetry tracing and Prometheus metrics."""

import logging

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

from app.config import Settings

tracer = trace.get_tracer("testlens")

AGENT_REQUESTS = Counter(
    "testlens_agent_requests_total", "Questions answered by the agent", ["provider", "outcome"]
)
AGENT_LATENCY = Histogram(
    "testlens_agent_request_seconds", "End-to-end agent latency per question", ["provider"]
)
TOOL_CALLS = Counter(
    "testlens_agent_tool_calls_total", "Agent tool invocations", ["tool", "cache", "outcome"]
)
LLM_CALLS = Counter("testlens_llm_calls_total", "LLM completion calls", ["provider", "outcome"])


def _add_trace_context(_logger, _method, event_dict):
    span = trace.get_current_span().get_span_context()
    if span.is_valid:
        event_dict["trace_id"] = format(span.trace_id, "032x")
        event_dict["span_id"] = format(span.span_id, "016x")
    return event_dict


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_trace_context,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def configure_tracing(settings: Settings) -> None:
    """Install a tracer provider; export over OTLP/HTTP when an endpoint is configured."""
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.otel_service_name}))
    if settings.otel_exporter_otlp_endpoint:
        endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces"
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
