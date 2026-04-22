from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ReviewCategory = Literal[
    "security",
    "performance",
    "style",
    "maintainability",
    "testing",
    "correctness",
]
SeverityLevel = Literal["low", "medium", "high", "critical"]
ReviewerRole = Literal["primary", "secondary", "tertiary", "fallback"]


class Finding(BaseModel):
    category: ReviewCategory
    severity: SeverityLevel = "medium"
    title: str
    description: str
    line_start: int | None = None
    line_end: int | None = None
    recommendation: str | None = None


class ModelReview(BaseModel):
    model_name: str
    role: ReviewerRole
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=10.0)
    success: bool = True
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class ReviewRequest(BaseModel):
    user_id: str = Field(min_length=1)
    repository: str | None = None
    file_path: str | None = None
    language: str = "python"
    code: str = Field(min_length=1)
    diff: str | None = None
    focus: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResponse(BaseModel):
    review_id: str
    user_id: str
    repository: str | None = None
    file_path: str | None = None
    language: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    refactoring_suggestions: list[str] = Field(default_factory=list)
    test_recommendations: list[str] = Field(default_factory=list)
    model_results: list[ModelReview] = Field(default_factory=list)
    consensus_score: float = Field(ge=0.0, le=10.0)
    cache_hit: bool = False
    html_report: str | None = None
    processing_ms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchReviewRequest(BaseModel):
    items: list[ReviewRequest]

    @model_validator(mode="after")
    def validate_items_not_empty(self) -> "BatchReviewRequest":
        if not self.items:
            raise ValueError("Batch request must include at least one item.")
        return self


class BatchReviewResponse(BaseModel):
    items: list[ReviewResponse] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)


class ReviewHistoryItem(BaseModel):
    review_id: str
    user_id: str
    repository: str | None = None
    file_path: str | None = None
    overall_score: float
    cache_hit: bool = False
    created_at: datetime


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    redis: bool
    database: bool
    environment: str
