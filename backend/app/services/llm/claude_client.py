import logging

from anthropic import AsyncAnthropic

from backend.app.core.config import Settings
from backend.app.models.review import ModelReview, ReviewerRole
from backend.app.services.llm.base import BaseReviewer, parse_model_response

logger = logging.getLogger(__name__)


class ClaudeReviewer(BaseReviewer):
    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.anthropic_model
        self._enabled = bool(settings.anthropic_api_key)
        self._client = (
            AsyncAnthropic(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else None
        )

    async def review(self, prompt: str, role: ReviewerRole = "primary") -> ModelReview:
        if not self._enabled or self._client is None:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary="Claude API key not configured.",
                score=0.0,
                findings=[],
                success=False,
                error="missing_anthropic_key",
            )

        try:
            response = await self._client.messages.create(
                model=self.model_name,
                max_tokens=1200,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            text_parts: list[str] = []
            for block in response.content:
                block_text = getattr(block, "text", None)
                if block_text:
                    text_parts.append(block_text)
            payload_text = "\n".join(text_parts)
            return parse_model_response(
                text=payload_text,
                model_name=self.model_name,
                role=role,
                fallback_score=5.8,
            )
        except Exception as exc:
            logger.exception("Claude review failed: %s", exc)
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary="Claude request failed.",
                findings=[],
                score=0.0,
                success=False,
                error=str(exc),
            )
