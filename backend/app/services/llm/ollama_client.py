"""Ollama LLM client for free local code review."""

import json
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.models.review import Finding, ModelReview, ReviewerRole
from backend.app.services.llm.base import BaseReviewer


class OllamaReviewer(BaseReviewer):
    """Reviewer using Ollama local models."""

    def __init__(self, settings: Settings, model_name: str) -> None:
        self.model_name = model_name
        self.base_url = settings.ollama_base_url
        self.timeout = settings.ollama_timeout

    async def review(self, prompt: str, role: ReviewerRole = "primary") -> ModelReview:
        """Send review request to Ollama and parse response."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data.get("response", "")

                findings = self._parse_findings(raw_text)
                score = self._extract_score(raw_text, findings)
                summary = self._extract_summary(raw_text, findings)

                return ModelReview(
                    model_name=self.model_name,
                    role=role,
                    summary=summary,
                    findings=findings,
                    score=score,
                    success=True,
                    raw_response={"text": raw_text[:500]},
                )

        except httpx.TimeoutException:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama model {self.model_name} timed out.",
                findings=[],
                score=0.0,
                success=False,
                error="timeout",
            )
        except httpx.HTTPStatusError as e:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama HTTP error: {e.response.status_code}",
                findings=[],
                score=0.0,
                success=False,
                error=f"http_{e.response.status_code}",
            )
        except Exception as e:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama error: {str(e)}",
                findings=[],
                score=0.0,
                success=False,
                error=str(e),
            )

    def _parse_findings(self, text: str) -> list[Finding]:
        """Extract findings from Ollama response."""
        findings: list[Finding] = []

        # Try to parse JSON if present
        if "```json" in text.lower():
            try:
                json_start = text.lower().find("```json") + 7
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
                data = json.loads(json_str)

                if isinstance(data, dict) and "findings" in data:
                    for item in data["findings"]:
                        findings.append(
                            Finding(
                                category=item.get("category", "general"),
                                severity=item.get("severity", "medium"),
                                title=item.get("title", "Issue detected"),
                                description=item.get("description", ""),
                                recommendation=item.get("recommendation", ""),
                            )
                        )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        # Fallback: parse text-based findings
        if not findings:
            lines = text.split("\n")
            current_finding: dict[str, Any] = {}

            for line in lines:
                line_lower = line.lower().strip()

                # Detect severity keywords
                if any(word in line_lower for word in ["critical", "high", "security"]):
                    if current_finding:
                        findings.append(Finding(**current_finding))
                    current_finding = {
                        "category": "security",
                        "severity": "high",
                        "title": line.strip("- *#").strip(),
                        "description": "",
                        "recommendation": "",
                    }
                elif any(word in line_lower for word in ["performance", "slow", "inefficient"]):
                    if current_finding:
                        findings.append(Finding(**current_finding))
                    current_finding = {
                        "category": "performance",
                        "severity": "medium",
                        "title": line.strip("- *#").strip(),
                        "description": "",
                        "recommendation": "",
                    }
                elif any(word in line_lower for word in ["bug", "error", "incorrect"]):
                    if current_finding:
                        findings.append(Finding(**current_finding))
                    current_finding = {
                        "category": "correctness",
                        "severity": "medium",
                        "title": line.strip("- *#").strip(),
                        "description": "",
                        "recommendation": "",
                    }
                elif current_finding and line.strip():
                    # Add to description
                    if not current_finding["description"]:
                        current_finding["description"] = line.strip()
                    else:
                        current_finding["description"] += " " + line.strip()

            if current_finding:
                findings.append(Finding(**current_finding))

        return findings[:10]  # Limit to 10 findings

    def _extract_score(self, text: str, findings: list[Finding]) -> float:
        """Extract or calculate quality score."""
        # Try to find explicit score
        for line in text.split("\n"):
            if "score" in line.lower() or "rating" in line.lower():
                # Look for numbers like 7.5, 8/10, etc.
                import re

                numbers = re.findall(r"\d+\.?\d*", line)
                if numbers:
                    score = float(numbers[0])
                    # Normalize to 0-10 scale
                    if score > 10:
                        score = score / 10
                    return min(10.0, max(0.0, score))

        # Calculate based on findings
        base_score = 8.5
        deduction = len(findings) * 0.8
        for finding in findings:
            if finding.severity == "high":
                deduction += 0.5
            elif finding.severity == "critical":
                deduction += 1.0

        return max(0.0, min(10.0, base_score - deduction))

    def _extract_summary(self, text: str, findings: list[Finding]) -> str:
        """Extract or generate summary."""
        lines = text.split("\n")

        # Try to find summary section
        for i, line in enumerate(lines):
            if "summary" in line.lower() and i + 1 < len(lines):
                summary = lines[i + 1].strip()
                if summary and len(summary) > 20:
                    return summary[:300]

        # Generate summary based on findings
        if not findings:
            return "Code review completed. No major issues detected."

        issue_count = len(findings)
        high_severity = sum(1 for f in findings if f.severity in ["high", "critical"])

        if high_severity > 0:
            return (
                f"Found {issue_count} issue(s) including {high_severity} "
                f"high-severity concern(s). Review recommended."
            )
        else:
            return f"Found {issue_count} minor issue(s). Code is generally acceptable."
