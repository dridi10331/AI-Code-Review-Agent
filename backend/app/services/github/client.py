import base64
from collections.abc import Iterable
from pathlib import Path

import httpx

from backend.app.models.review import ReviewRequest, ReviewResponse

PR_ACTIONS_TO_PROCESS = {"opened", "synchronize", "reopened", "ready_for_review"}


class GitHubApiClient:
    def __init__(
        self,
        token: str | None,
        base_url: str,
        max_files: int,
        max_file_chars: int,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-code-review-agent",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=25.0,
        )
        self._max_files = max_files
        self._max_file_chars = max_file_chars

    async def aclose(self) -> None:
        await self._client.aclose()

    async def build_requests_from_pull_request(
        self,
        event: str,
        payload: dict,
    ) -> list[ReviewRequest]:
        if event != "pull_request":
            return []

        action = str(payload.get("action", ""))
        if action not in PR_ACTIONS_TO_PROCESS:
            return []

        repository = payload.get("repository", {})
        full_name = repository.get("full_name")
        pull_request = payload.get("pull_request", {})
        pr_number = pull_request.get("number")
        head = pull_request.get("head", {})
        head_sha = head.get("sha")

        if not full_name or not pr_number or not head_sha:
            return []

        owner, repo = full_name.split("/", 1)
        files = await self._list_pull_request_files(owner, repo, int(pr_number))

        sender = payload.get("sender", {})
        user_id = sender.get("login") or "github-webhook"

        requests: list[ReviewRequest] = []
        for item in files:
            filename = item.get("filename")
            if not filename:
                continue

            status = str(item.get("status", ""))
            if status == "removed":
                continue

            patch = item.get("patch")
            if not patch and item.get("changes", 0) == 0:
                continue

            content = await self._fetch_file_content(owner, repo, filename, head_sha)
            if not content:
                continue

            requests.append(
                ReviewRequest(
                    user_id=user_id,
                    repository=full_name,
                    file_path=filename,
                    language=_infer_language(filename),
                    code=content,
                    diff=patch,
                    focus=["security", "performance", "maintainability"],
                    metadata={
                        "source": "github_webhook_pr",
                        "event": event,
                        "action": action,
                        "pr_number": pr_number,
                        "sha": head_sha,
                    },
                )
            )

        return requests

    async def _list_pull_request_files(self, owner: str, repo: str, pull_number: int) -> list[dict]:
        files: list[dict] = []
        page = 1

        while len(files) < self._max_files:
            response = await self._client.get(
                f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
                params={"per_page": 100, "page": page},
            )
            if response.status_code >= 400:
                return files

            page_items = _as_dict_list(response.json())
            if not page_items:
                break

            files.extend(page_items)
            page += 1

        return files[: self._max_files]

    async def _fetch_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str,
    ) -> str | None:
        response = await self._client.get(
            f"/repos/{owner}/{repo}/contents/{file_path}",
            params={"ref": ref},
        )
        if response.status_code >= 400:
            return None

        payload = response.json()
        if not isinstance(payload, dict):
            return None

        encoding = payload.get("encoding")
        content = payload.get("content")
        if encoding != "base64" or not isinstance(content, str):
            return None

        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            return None

        return decoded[: self._max_file_chars]

    async def post_pr_review_comment(
        self,
        full_name: str,
        pr_number: int,
        reviews: list[ReviewResponse],
    ) -> bool:
        """Post aggregated review results as a single PR comment (like Bito)."""
        if not reviews:
            return False

        owner, repo = full_name.split("/", 1)
        body = _format_pr_comment(reviews)

        response = await self._client.post(
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        return response.status_code in (200, 201)

    async def post_pr_status(
        self,
        full_name: str,
        sha: str,
        reviews: list[ReviewResponse],
    ) -> bool:
        """Post a GitHub commit status check based on review scores."""
        if not reviews:
            return False

        owner, repo = full_name.split("/", 1)
        avg_score = sum(r.consensus_score for r in reviews) / len(reviews)
        total_high = sum(
            1 for r in reviews
            for f in r.findings
            if f.severity in ("high", "critical")
        )

        if total_high > 0 or avg_score < 5.0:
            state = "failure"
            description = f"AI Review: {total_high} high-severity issue(s) found. Score: {avg_score:.1f}/10"
        elif avg_score < 7.0:
            state = "pending"
            description = f"AI Review: Minor issues found. Score: {avg_score:.1f}/10"
        else:
            state = "success"
            description = f"AI Review: Code looks good! Score: {avg_score:.1f}/10"

        response = await self._client.post(
            f"/repos/{owner}/{repo}/statuses/{sha}",
            json={
                "state": state,
                "description": description,
                "context": "ai-code-review-agent",
                "target_url": "",
            },
        )
        return response.status_code in (200, 201)


def _format_pr_comment(reviews: list[ReviewResponse]) -> str:
    """Format review results into a GitHub PR comment (Markdown)."""
    avg_score = sum(r.consensus_score for r in reviews) / len(reviews)
    total_findings = sum(len(r.findings) for r in reviews)
    high_findings = sum(
        1 for r in reviews for f in r.findings if f.severity in ("high", "critical")
    )

    score_emoji = "🟢" if avg_score >= 7 else "🟡" if avg_score >= 5 else "🔴"
    lines: list[str] = [
        "## 🤖 AI Code Review",
        "",
        f"**Consensus Score:** {score_emoji} `{avg_score:.1f}/10`  "
        f"| **Files Reviewed:** `{len(reviews)}`  "
        f"| **Total Findings:** `{total_findings}`  "
        f"| **High Severity:** `{high_findings}`",
        "",
        "---",
        "",
    ]

    for review in reviews:
        lines.append(f"### 📄 `{review.file_path or 'unknown'}`")
        lines.append("")
        lines.append(f"**Score:** `{review.consensus_score:.1f}/10`")
        lines.append("")
        lines.append(f"> {review.summary}")
        lines.append("")

        if review.findings:
            lines.append("<details>")
            lines.append(f"<summary><strong>Findings ({len(review.findings)})</strong></summary>")
            lines.append("")
            for finding in review.findings:
                sev_emoji = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    finding.severity, "⚪"
                )
                lines.append(f"#### {sev_emoji} [{finding.severity.upper()}] {finding.title}")
                lines.append(f"- **Category:** {finding.category}")
                if finding.description:
                    lines.append(f"- **Details:** {finding.description[:300]}")
                if finding.recommendation:
                    lines.append(f"- **Fix:** {finding.recommendation}")
                if finding.line_start:
                    lines.append(f"- **Line:** {finding.line_start}")
                lines.append("")
            lines.append("</details>")
            lines.append("")

        if review.refactoring_suggestions:
            lines.append("<details>")
            lines.append("<summary><strong>Refactoring Suggestions</strong></summary>")
            lines.append("")
            for suggestion in review.refactoring_suggestions[:3]:
                lines.append(f"- {suggestion}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(
        "_Powered by [AI Code Review Agent](https://github.com/dridi10331/AI-Code-Review-Agent) "
        "— Multi-model ensemble with Claude, OpenAI & Ollama_"
    )

    return "\n".join(lines)


def _as_dict_list(value: object) -> list[dict]:
    if not isinstance(value, Iterable):
        return []
    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _infer_language(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".java": "java",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".c": "c",
        ".kt": "kotlin",
        ".swift": "swift",
        ".sql": "sql",
    }
    return mapping.get(suffix, "text")
