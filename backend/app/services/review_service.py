import asyncio
import time
import uuid
from contextlib import suppress

from opentelemetry import trace

from backend.app.db.repository import ReviewRepository
from backend.app.models.review import (
    BatchReviewResponse,
    ReviewHistoryItem,
    ReviewRequest,
    ReviewResponse,
)
from backend.app.services.cache.semantic_cache import SemanticCache
from backend.app.services.llm.ensemble import MultiModelEnsemble
from backend.app.services.reports.html_report import HtmlReportService
from backend.app.utils.hashing import normalized_code_hash

tracer = trace.get_tracer(__name__)


class ReviewService:
    def __init__(
        self,
        ensemble: MultiModelEnsemble,
        semantic_cache: SemanticCache,
        repository: ReviewRepository,
        html_report_service: HtmlReportService,
    ) -> None:
        self._ensemble = ensemble
        self._semantic_cache = semantic_cache
        self._repository = repository
        self._html_report_service = html_report_service

    async def review_code(self, request: ReviewRequest) -> ReviewResponse:
        started = time.perf_counter()

        with tracer.start_as_current_span("review_code") as span:
            span.set_attribute("review.user_id", request.user_id)
            span.set_attribute("review.language", request.language)
            span.set_attribute("review.has_diff", bool(request.diff))

            with tracer.start_as_current_span("semantic_cache_lookup"):
                cached, _similarity = await self._semantic_cache.lookup(
                    request.code,
                    request.language,
                )
            if cached:
                cached.processing_ms = int((time.perf_counter() - started) * 1000)
                span.set_attribute("review.cache_hit", True)
                return cached

            span.set_attribute("review.cache_hit", False)
            with tracer.start_as_current_span("ensemble_review"):
                ensemble_result = await self._ensemble.review(request)
            review_id = str(uuid.uuid4())

            response = ReviewResponse(
                review_id=review_id,
                user_id=request.user_id,
                repository=request.repository,
                file_path=request.file_path,
                language=request.language,
                summary=ensemble_result["summary"],
                findings=ensemble_result["findings"],
                refactoring_suggestions=ensemble_result["refactoring_suggestions"],
                test_recommendations=ensemble_result["test_recommendations"],
                model_results=ensemble_result["model_results"],
                consensus_score=ensemble_result["consensus_score"],
                cache_hit=False,
                processing_ms=0,
            )

            response.html_report = self._html_report_service.generate(response)
            response.processing_ms = int((time.perf_counter() - started) * 1000)
            span.set_attribute("review.processing_ms", response.processing_ms)

            code_hash = normalized_code_hash(request.code, request.language)
            with tracer.start_as_current_span("persist_review"), suppress(Exception):
                await self._repository.create_review(
                    request=request,
                    response=response,
                    code_hash=code_hash,
                )

            with tracer.start_as_current_span("semantic_cache_store"):
                await self._semantic_cache.store(request.code, request.language, response)

            return response

    async def review_batch(self, requests: list[ReviewRequest]) -> BatchReviewResponse:
        results: list[ReviewResponse] = []
        failed: list[dict] = []

        max_concurrency = 4
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run(index: int, item: ReviewRequest) -> tuple[int, ReviewResponse | None, str | None]:
            try:
                async with semaphore:
                    result = await self.review_code(item)
                return index, result, None
            except Exception as exc:
                return index, None, str(exc)

        tasks = [_run(index, item) for index, item in enumerate(requests)]
        for index, result, error in await asyncio.gather(*tasks):
            if result is not None:
                results.append(result)
            else:
                failed.append({"index": index, "error": error or "unknown_error"})

        failed.sort(key=lambda item: item["index"])
        return BatchReviewResponse(items=results, failed=failed)

    async def get_review(self, review_id: str) -> ReviewResponse | None:
        record = await self._repository.get_review(review_id)
        if not record:
            return None
        payload = record.get("response_payload")
        if not payload:
            return None
        return ReviewResponse.model_validate(payload)

    async def get_history(
        self,
        user_id: str | None,
        limit: int,
        offset: int,
    ) -> list[ReviewHistoryItem]:
        try:
            return await self._repository.list_history(user_id=user_id, limit=limit, offset=offset)
        except Exception:
            # Database connection failed (e.g., asyncpg on Windows)
            # Return empty list instead of crashing
            return []
