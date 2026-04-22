import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from backend.app.models.review import Finding, ModelReview, ReviewerRole

logger = logging.getLogger(__name__)


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

    raw_findings = payload.get("findings", [])
    findings: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        try:
            findings.append(
                Finding(
                    category=item.get("category", "maintainability"),
                    severity=item.get("severity", "medium"),
                    title=item.get("title", "Untitled finding"),
                    description=item.get("description", "No description provided."),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    recommendation=item.get("recommendation"),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed finding: %s", exc)

    summary = payload.get("summary", "No summary returned.")
    score = payload.get("score", fallback_score)

    try:
        score_float = max(0.0, min(10.0, float(score)))
    except (TypeError, ValueError):
        score_float = fallback_score

    return ModelReview(
        model_name=model_name,
        role=role,
        summary=summary,
        findings=findings,
        score=score_float,
        success=True,
        raw_response=payload,
    )
