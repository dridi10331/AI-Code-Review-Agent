import logging

from openai import AsyncOpenAI

from backend.app.core.config import Settings
from backend.app.models.review import ModelReview, ReviewerRole
from backend.app.services.llm.base import BaseReviewer, parse_model_response

logger = logging.getLogger(__name__)


class OpenAIReviewer(BaseReviewer):
    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.openai_model
        self._enabled = bool(settings.openai_api_key)
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )

    async def review(self, prompt: str, role: ReviewerRole = "secondary") -> ModelReview:
        if not self._enabled or self._client is None:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary="OpenAI API key not configured.",
                score=0.0,
                findings=[],
                success=False,
                error="missing_openai_key",
            )

        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strict code reviewer. Return valid JSON only.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            content = response.choices[0].message.content or ""
            return parse_model_response(
                text=content,
                model_name=self.model_name,
                role=role,
                fallback_score=5.5,
            )
        except Exception as exc:
            logger.exception("OpenAI review failed: %s", exc)
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary="OpenAI request failed.",
                findings=[],
                score=0.0,
                success=False,
                error=str(exc),
            )
