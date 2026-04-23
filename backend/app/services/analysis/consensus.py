from collections import defaultdict

from backend.app.models.review import Finding, ModelReview

ROLE_WEIGHTS = {
    "primary": 0.5,
    "secondary": 0.3,
    "tertiary": 0.2,
    "fallback": 0.3,
}

SEVERITY_PENALTIES = {
    "low": 0.2,
    "medium": 0.6,
    "high": 1.1,
    "critical": 1.8,
}


def aggregate_findings(model_results: list[ModelReview]) -> list[Finding]:
    deduplicated: dict[tuple[str, str, int | None], Finding] = {}
    for result in model_results:
        for finding in result.findings:
            key = (finding.category, finding.title.lower(), finding.line_start)
            if key not in deduplicated:
                deduplicated[key] = finding
            else:
                existing = deduplicated[key]
                if finding.severity in ("high", "critical") and existing.severity in (
                    "low",
                    "medium",
                ):
                    deduplicated[key] = finding
    return list(deduplicated.values())


def compute_consensus_score(model_results: list[ModelReview], findings: list[Finding]) -> float:
    if not model_results:
        return 0.0

    # Only include successful models in consensus calculation
    successful_results = [r for r in model_results if r.success]
    if not successful_results:
        return 0.0

    weighted_score = 0.0
    total_weight = 0.0
    for model_result in successful_results:
        weight = ROLE_WEIGHTS.get(model_result.role, 0.2)
        weighted_score += model_result.score * weight
        total_weight += weight

    base_score = weighted_score / max(total_weight, 1e-9)

    penalty = 0.0
    for finding in findings:
        penalty += SEVERITY_PENALTIES.get(finding.severity, 0.4)

    adjusted_score = max(0.0, min(10.0, base_score - penalty * 0.35))
    return round(adjusted_score, 2)


def build_summary(findings: list[Finding]) -> str:
    if not findings:
        return (
            "No major issues detected. "
            "Code quality appears solid with minor improvement opportunities."
        )

    category_count: dict[str, int] = defaultdict(int)
    critical_count = 0
    high_count = 0

    for finding in findings:
        category_count[finding.category] += 1
        if finding.severity == "critical":
            critical_count += 1
        elif finding.severity == "high":
            high_count += 1

    category_text = ", ".join(
        f"{count} {category}" for category, count in sorted(category_count.items())
    )

    risk_note = []
    if critical_count:
        risk_note.append(f"{critical_count} critical")
    if high_count:
        risk_note.append(f"{high_count} high severity")

    risk_suffix = f" Includes {' and '.join(risk_note)} findings." if risk_note else ""
    return f"Detected {len(findings)} findings across {category_text}.{risk_suffix}"
