import asyncio

from backend.app.models.review import Finding, ModelReview, ReviewRequest
from backend.app.services.analysis.consensus import (
    aggregate_findings,
    build_summary,
    compute_consensus_score,
)
from backend.app.services.llm.circuit_breaker import CircuitBreaker
from backend.app.services.llm.prompts import (
    build_performance_prompt,
    build_primary_prompt,
    build_security_prompt,
)


class MultiModelEnsemble:
    def __init__(
        self,
        claude_reviewer,  # Can be ClaudeReviewer or OllamaReviewer
        openai_reviewer,  # Can be OpenAIReviewer or OllamaReviewer
        heuristic_reviewer,  # Can be HeuristicReviewer or OllamaReviewer
        circuit_breaker: CircuitBreaker,
    ) -> None:
        self._claude_reviewer = claude_reviewer
        self._openai_reviewer = openai_reviewer
        self._heuristic_reviewer = heuristic_reviewer
        self._circuit_breaker = circuit_breaker

    async def review(self, request: ReviewRequest) -> dict:
        primary_prompt = build_primary_prompt(request)
        security_prompt = build_security_prompt(request)

        primary_task = self._run_primary_with_fallback(primary_prompt)
        secondary_task = self._run_secondary(security_prompt)
        tertiary_task = self._heuristic_reviewer.review(request.code, role="tertiary")

        model_results = await asyncio.gather(primary_task, secondary_task, tertiary_task)
        model_results = [result for result in model_results if isinstance(result, ModelReview)]

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
                summary="OpenAI reviewer skipped because circuit breaker is open.",
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

        # Preserve order while deduplicating.
        unique_tests = list(dict.fromkeys(tests))
        return unique_tests[:8]
