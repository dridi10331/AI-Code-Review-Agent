import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.api.deps import get_app_settings, get_container
from backend.app.core.config import Settings
from backend.app.core.container import ServiceContainer
from backend.app.services.github.webhook import extract_review_requests, verify_github_signature

router = APIRouter(prefix="")


@router.post("/github")
async def github_webhook(
    request: Request,
    container: Annotated[ServiceContainer, Depends(get_container)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict:
    """Process GitHub webhook events for PR code review.
    
    Args:
        request: HTTP request with webhook payload
        container: Service container
        settings: Application settings
        
    Returns:
        dict: Processing result with status and item count
        
    Raises:
        HTTPException: For invalid signature or malformed payload
    """
    payload_bytes = await request.body()
    
    # Validate payload size to prevent DoS
    if len(payload_bytes) > 10_000_000:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload too large.",
        )
    
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_github_signature(
        payload_bytes,
        signature,
        settings.github_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature.",
        )

    event = request.headers.get("X-GitHub-Event", "unknown")
    try:
        payload = json.loads(payload_bytes.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc
    
    try:
        review_requests = await extract_review_requests(
            event,
            payload,
            container.github_client,
        )
    except Exception as exc:
        # Log error but don't crash - webhook processing should be resilient
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to extract review requests: {exc}")
        review_requests = []

    if not review_requests:
        return {
            "status": "accepted",
            "event": event,
            "processed": 0,
            "message": "No inline review payloads or pull request files to analyze.",
        }

    for item in review_requests:
        await container.rate_limiter.enforce(item.user_id)

    batch_result = await container.review_service.review_batch(review_requests)

    # Post results back to the PR as a comment (like Bito)
    if event == "pull_request" and batch_result.items:
        pr_meta = _extract_pr_meta(payload)
        if pr_meta:
            try:
                full_name, pr_number, head_sha = pr_meta
                await container.github_client.post_pr_review_comment(
                    full_name, pr_number, batch_result.items
                )
                await container.github_client.post_pr_status(
                    full_name, head_sha, batch_result.items
                )
            except Exception as exc:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to post GitHub comments: {exc}")
                # Don't fail the webhook if comment posting fails

    return {
        "status": "processed",
        "event": event,
        "processed": len(batch_result.items),
        "failed": batch_result.failed,
    }


def _extract_pr_meta(payload: dict) -> tuple[str, int, str] | None:
    """Extract repo full name, PR number and head SHA from a webhook payload."""
    repository = payload.get("repository", {})
    full_name = repository.get("full_name")
    pull_request = payload.get("pull_request", {})
    pr_number = pull_request.get("number")
    head_sha = pull_request.get("head", {}).get("sha")
    if full_name and pr_number and head_sha:
        return full_name, int(pr_number), head_sha
    return None
