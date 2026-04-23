from langchain_core.prompts import PromptTemplate

from backend.app.models.review import ReviewRequest
from backend.app.services.analysis.diff_parser import summarize_diff

JSON_CONTRACT = """
Return strict JSON with this structure:
{
  "summary": "string",
  "score": number between 0 and 10,
  "findings": [
    {
      "category": "security|performance|style|maintainability|testing|correctness",
      "severity": "low|medium|high|critical",
      "title": "short title",
      "description": "detailed description",
      "line_start": number or null,
      "line_end": number or null,
      "recommendation": "specific fix"
    }
  ]
}
""".strip()

PRIMARY_TEMPLATE = PromptTemplate.from_template(
    """
You are a principal staff engineer performing a deep code review.
Focus: correctness, maintainability, architecture, style, and refactoring opportunities.
Language: {language}
Requested Focus Areas: {focus}
Diff Summary:
{diff_summary}

Code:
{code}

{json_contract}
""".strip()
)

SECURITY_TEMPLATE = PromptTemplate.from_template(
    """
You are an application security engineer.
Find vulnerabilities, unsafe patterns, secrets handling issues,
auth mistakes, and injection vectors.
Language: {language}
Diff Summary:
{diff_summary}

Code:
{code}

{json_contract}
""".strip()
)

PERFORMANCE_TEMPLATE = PromptTemplate.from_template(
    """
You are a performance optimization expert.
Focus on algorithmic complexity, memory pressure, repeated I/O, and async misuse.
Language: {language}
Diff Summary:
{diff_summary}

Code:
{code}

{json_contract}
""".strip()
)


def build_primary_prompt(request: ReviewRequest) -> str:
    return PRIMARY_TEMPLATE.format(
        language=request.language,
        focus=", ".join(request.focus) if request.focus else "general review",
        diff_summary=summarize_diff(request.diff or ""),
        code=request.code,
        json_contract=JSON_CONTRACT,
    )


def build_security_prompt(request: ReviewRequest) -> str:
    return SECURITY_TEMPLATE.format(
        language=request.language,
        diff_summary=summarize_diff(request.diff or ""),
        code=request.code,
        json_contract=JSON_CONTRACT,
    )


def build_performance_prompt(request: ReviewRequest) -> str:
    return PERFORMANCE_TEMPLATE.format(
        language=request.language,
        diff_summary=summarize_diff(request.diff or ""),
        code=request.code,
        json_contract=JSON_CONTRACT,
    )
