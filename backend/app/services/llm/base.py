import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from backend.app.models.review import Finding, ModelReview, ReviewerRole
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

class LlmReviewPayload(BaseModel):
    summary: str = Field(default="No summary returned.")
    score: float = Field(default=5.0, ge=0.0, le=10.0)
    findings: list[Finding] = Field(default_factory=list)


class BaseReviewer(ABC):
    model_name: str

    @abstractmethod
    async def review(self, prompt: str, role: ReviewerRole) -> ModelReview:
        raise NotImplementedError


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def parse_model_response(
    *,
    text: str,
    model_name: str,
    role: ReviewerRole,
    fallback_score: float = 5.0,
) -> ModelReview:
    payload = _extract_json_payload(text)
    if payload is None:
        return ModelReview(
            model_name=model_name,
            role=role,
            summary=text[:500] or "Model did not return valid JSON output.",
            findings=[],
            score=fallback_score,
            success=False,
            error="Invalid JSON response format",
            raw_response={"raw_text": text[:1500]},
        )

    try:
        normalized = LlmReviewPayload.model_validate(
            {
                "summary": payload.get("summary", "No summary returned."),
                "score": payload.get("score", fallback_score),
                "findings": payload.get("findings", []),
            }
        )
    except ValidationError as exc:
        logger.debug("Invalid model payload: %s", exc)
        return ModelReview(
            model_name=model_name,
            role=role,
            summary=str(payload.get("summary") or text[:300] or "Model returned invalid JSON payload."),
            findings=[],
            score=fallback_score,
            success=False,
            error="invalid_payload_schema",
            raw_response={"payload": payload, "validation_error": exc.errors()},
        )

    return ModelReview(
        model_name=model_name,
        role=role,
        summary=normalized.summary,
        findings=normalized.findings,
        score=normalized.score,
        success=True,
        raw_response=payload,
    )
