from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class ToolCallOut(BaseModel):
    tool: str
    arguments: dict[str, Any]
    rows: list[dict[str, Any]]
    cached: bool
    error: str | None = None


class AskResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[ToolCallOut]
