import re

from backend.app.models.review import Finding, ModelReview, ReviewerRole
from backend.app.services.llm.base import BaseReviewer


class HeuristicReviewer(BaseReviewer):
    def __init__(self) -> None:
        self.model_name = "heuristic-oss-performance"

    async def review(self, prompt: str, role: ReviewerRole = "tertiary") -> ModelReview:
        code = prompt
        findings: list[Finding] = []

        if "eval(" in code:
            findings.append(
                Finding(
                    category="security",
                    severity="high",
                    title="Dynamic eval usage",
                    description=(
                        "Use of eval can enable code injection "
                        "if untrusted input reaches it."
                    ),
                    recommendation=(
                        "Replace eval with explicit parsing "
                        "or safe expression evaluators."
                    ),
                )
            )

        if re.search(r"for\s+\w+\s+in\s+.*:\n\s+for\s+\w+\s+in\s+", code, re.MULTILINE):
            findings.append(
                Finding(
                    category="performance",
                    severity="medium",
                    title="Nested loops detected",
                    description="Nested iteration can degrade performance at scale.",
                    recommendation=(
                        "Consider indexing or hash-map based lookups "
                        "to reduce complexity."
                    ),
                )
            )

        if "requests.get(" in code and "timeout=" not in code:
            findings.append(
                Finding(
                    category="correctness",
                    severity="medium",
                    title="HTTP request without timeout",
                    description=(
                        "Network requests without timeout "
                        "can hang worker threads."
                    ),
                    recommendation="Set explicit timeout values for external calls.",
                )
            )

        long_function_detected = False
        current_length = 0
        for line in code.splitlines():
            if line.strip().startswith("def "):
                current_length = 0
            if line.strip():
                current_length += 1
            if current_length > 80:
                long_function_detected = True

        if long_function_detected:
            findings.append(
                Finding(
                    category="maintainability",
                    severity="low",
                    title="Large function complexity",
                    description="Long functions are difficult to test and maintain.",
                    recommendation="Extract cohesive helper functions and isolate side effects.",
                )
            )

        score = max(0.0, min(10.0, 8.5 - 0.7 * len(findings)))
        if findings:
            summary = f"Heuristic analyzer flagged {len(findings)} potential issue(s)."
        else:
            summary = "Heuristic analyzer did not detect major performance anti-patterns."

        return ModelReview(
            model_name=self.model_name,
            role=role,
            summary=summary,
            findings=findings,
            score=score,
            success=True,
            raw_response={"rule_count": 4},
        )
