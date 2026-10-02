from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.agent.agent import Agent, AgentError
from app.agent.providers.base import LLMError
from app.schemas import AskRequest, AskResponse

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    state = request.app.state
    try:
        async with state.sessionmaker() as session:
            await session.execute(text("SELECT 1"))
        await state.redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="dependencies unavailable") from exc
    return {"status": "ready"}


@router.post("/api/ask", response_model=AskResponse)
async def ask(body: AskRequest, request: Request) -> AskResponse:
    agent: Agent = request.app.state.agent
    try:
        result = await agent.ask(body.question, body.session_id)
    except (LLMError, AgentError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskResponse.model_validate(asdict(result))
