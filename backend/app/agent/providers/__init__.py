from app.agent.providers.base import LLMProvider
from app.config import Settings


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "anthropic":
        from app.agent.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            model=settings.anthropic_model,
            effort=settings.anthropic_effort,
            max_tokens=settings.anthropic_max_tokens,
        )
    from app.agent.providers.fake import FakeProvider

    return FakeProvider()
