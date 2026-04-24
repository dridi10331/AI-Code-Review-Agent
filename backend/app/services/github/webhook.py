import hashlib
import hmac
from typing import Any

from backend.app.models.review import ReviewRequest
from backend.app.services.github.client import GitHubApiClient


def verify_github_signature(payload: bytes, signature_header: str | None, secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _extract_inline_review_requests(event: str, payload: dict[str, Any]) -> list[ReviewRequest]:
    requests: list[ReviewRequest] = []

    # Custom payload path intended for CI jobs that pass changed file content directly.
    review_payloads = payload.get("review_payloads")
    if isinstance(review_payloads, list):
        for item in review_payloads:
            if not isinstance(item, dict):
                continue
            code = item.get("code")
            user_id = item.get("user_id") or "github-webhook"
            if not code:
                continue
            requests.append(
                ReviewRequest(
                    user_id=user_id,
                    repository=item.get("repository")
                    or payload.get("repository", {}).get("full_name"),
                    file_path=item.get("file_path"),
                    language=item.get("language", "python"),
                    code=code,
                    diff=item.get("diff"),
                    focus=item.get("focus") or ["security", "performance", "maintainability"],
                    metadata={
                        "source": "github_webhook",
                        "event": event,
                        "raw_action": payload.get("action"),
                    },
                )
            )

    return requests


async def extract_review_requests(
    event: str,
    payload: dict[str, Any],
    github_client: GitHubApiClient,
) -> list[ReviewRequest]:
    inline_requests = _extract_inline_review_requests(event, payload)
    if inline_requests:
        return inline_requests

    return await github_client.build_requests_from_pull_request(event, payload)
