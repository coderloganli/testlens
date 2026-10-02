"""Tools the agent can call. Each validates its arguments and runs one read-only query."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app import queries
from app.agent.providers.base import ToolSpec


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FleetSummaryArgs(_Args):
    pass


class TopRiskDrivesArgs(_Args):
    limit: int = Field(10, ge=1, le=100, description="Maximum number of drives to return.")
    model: str | None = Field(None, description="Restrict to one drive model, e.g. ST12000NM0008.")
    min_probability: float = Field(
        0.0, ge=0.0, le=1.0, description="Only drives at or above this failure probability."
    )


class SmartHistoryArgs(_Args):
    serial_number: str = Field(description="Drive serial number.")
    days: int = Field(30, ge=1, le=365, description="Days of history to return.")


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    args_model: type[_Args]
    run: Callable[..., Awaitable[list[dict[str, Any]]]]


def _tool(
    name: str, description: str, args_model: type[_Args], run: Callable[..., Awaitable[Any]]
) -> Tool:
    return Tool(ToolSpec(name, description, args_model.model_json_schema()), args_model, run)


TOOLS: dict[str, Tool] = {
    t.spec.name: t
    for t in [
        _tool(
            "fleet_summary",
            "Per drive model: number of drives, number that have failed, and the mean of each "
            "drive's latest predicted failure probability.",
            FleetSummaryArgs,
            queries.fleet_summary,
        ),
        _tool(
            "top_risk_drives",
            "Drives ranked by their latest predicted failure probability, highest first, with "
            "model, datacenter, failure date if already failed, and prediction metadata.",
            TopRiskDrivesArgs,
            queries.top_risk_drives,
        ),
        _tool(
            "smart_history",
            "Daily SMART telemetry for one drive: power-on hours, reallocated, pending and "
            "offline-uncorrectable sectors, reported-uncorrectable errors, command timeouts, "
            "and temperature.",
            SmartHistoryArgs,
            queries.smart_history,
        ),
    ]
}


def tool_specs() -> list[ToolSpec]:
    return [t.spec for t in TOOLS.values()]
