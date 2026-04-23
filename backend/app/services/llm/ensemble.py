import asyncio

from backend.app.models.review import Finding, ModelReview, ReviewRequest
from backend.app.services.analysis.consensus import (
    aggregate_findings,
    build_summary,
    compute_consensus_score,
)
from backend.app.services.llm.circuit_breaker import CircuitBreaker
from backend.app.services.llm.ollama_client import OllamaReviewer
from backend.app.services.llm.prompts import (
    build_performance_prompt,
    build_primary_prompt,
    build_security_prompt,
)


class MultiModelEnsemble:
    def __init__(
        self,
        claude_reviewer,
        openai_reviewer,
        heuristic_reviewer,
        circuit_breaker: CircuitBreaker,
        ollama_mode: bool = False,
    ) -> None:
        self._claude_reviewer = claude_reviewer
        self._openai_reviewer = openai_reviewer
        self._heuristic_reviewer = heuristic_reviewer
        self._circuit_breaker = circuit_breaker
        # Sequential mode: Ollama can only handle one request at a time
        self._ollama_mode = ollama_mode

    async def review(self, request: ReviewRequest) -> dict:
        primary_prompt = build_primary_prompt(request)
        security_prompt = build_security_prompt(request)

        if self._ollama_mode:
            # Sequential execution — Ollama queues one request at a time
            model_results = await self._review_sequential(primary_prompt, security_prompt, request)
        else:
            # Parallel execution — for paid APIs (Claude + OpenAI)
            model_results = await self._review_parallel(primary_prompt, security_prompt, request)

        model_results = [r for r in model_results if isinstance(r, ModelReview)]
        findings = aggregate_findings(model_results)
        consensus_score = compute_consensus_score(model_results, findings)
        summary = build_summary(findings)

        return {
            "summary": summary,
            "findings": findings,
            "model_results": model_results,
            "consensus_score": consensus_score,
            "refactoring_suggestions": self._build_refactoring_suggestions(findings),
            "test_recommendations": self._build_test_recommendations(findings),
            "performance_prompt_used": build_performance_prompt(request),
        }

    async def _review_sequential(
        self, primary_prompt: str, security_prompt: str, request: ReviewRequest
    ) -> list[ModelReview]:
        """Run models one at a time — required for Ollama which is single-threaded."""
        results: list[ModelReview] = []

        # Primary review
        primary = await self._claude_reviewer.review(primary_prompt, role="primary")
        results.append(primary)

        # Secondary review (security-focused) — only if primary succeeded or we still want coverage
        secondary = await self._openai_reviewer.review(security_prompt, role="secondary")
        results.append(secondary)

        # Tertiary review (performance/heuristic)
        tertiary = await self._heuristic_reviewer.review(request.code, role="tertiary")
        results.append(tertiary)

        return results

    async def _review_parallel(
        self, primary_prompt: str, security_prompt: str, request: ReviewRequest
    ) -> list[ModelReview]:
        """Run all models in parallel — for paid APIs."""
        primary_task = self._run_primary_with_fallback(primary_prompt)
        secondary_task = self._run_secondary(security_prompt)
        tertiary_task = self._heuristic_reviewer.review(request.code, role="tertiary")
        return list(await asyncio.gather(primary_task, secondary_task, tertiary_task))

    async def _run_primary_with_fallback(self, prompt: str) -> ModelReview:
        primary = await self._claude_reviewer.review(prompt, role="primary")
        if primary.success:
            return primary
        fallback = await self._run_openai_with_circuit(prompt, role="fallback")
        if fallback.success:
            fallback.summary = f"Primary model unavailable. Fallback result: {fallback.summary}"
        return fallback

    async def _run_secondary(self, prompt: str) -> ModelReview:
        return await self._run_openai_with_circuit(prompt, role="secondary")

    async def _run_openai_with_circuit(self, prompt: str, role: str) -> ModelReview:
        if not self._circuit_breaker.allow_request():
            return ModelReview(
                model_name=self._openai_reviewer.model_name,
                role=role,
                summary="Reviewer skipped: circuit breaker open.",
                findings=[],
                score=0.0,
                success=False,
                error="circuit_breaker_open",
            )
        result = await self._openai_reviewer.review(prompt, role=role)
        if result.success:
            self._circuit_breaker.record_success()
        else:
            self._circuit_breaker.record_failure()
        return result

    @staticmethod
    def _build_refactoring_suggestions(findings: list[Finding]) -> list[str]:
        suggestions: list[str] = []
        for finding in findings:
            if finding.category in {"maintainability", "style", "correctness"}:
                suggestion = finding.recommendation or f"Address: {finding.title}"
                suggestions.append(suggestion)
        if not suggestions:
            suggestions.append("No major refactoring required; keep functions focused and typed.")
        return suggestions[:8]

    @staticmethod
    def _build_test_recommendations(findings: list[Finding]) -> list[str]:
        tests: list[str] = []
        for finding in findings:
            if finding.category == "security":
                tests.append("Add malicious-input test cases for security-sensitive paths.")
            if finding.category == "performance":
                tests.append("Add micro-benchmark or load test for hot paths.")
            if finding.category == "correctness":
                tests.append("Add regression tests that reproduce the identified edge case.")
        if not tests:
            tests.append("Add baseline unit tests for core business logic and edge inputs.")
        return list(dict.fromkeys(tests))[:8]
