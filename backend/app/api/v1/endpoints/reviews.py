from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_container, get_user_id, require_auth
from backend.app.core.container import ServiceContainer
from backend.app.models.review import (
    BatchReviewRequest,
    BatchReviewResponse,
    ReviewHistoryItem,
    ReviewRequest,
    ReviewResponse,
)
from backend.app.security.auth import AuthContext

router = APIRouter(prefix="")


@router.post("", response_model=ReviewResponse)
async def create_review(
    payload: ReviewRequest,
    container: Annotated[ServiceContainer, Depends(get_container)],
    header_user_id: Annotated[str, Depends(get_user_id)],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> ReviewResponse:
    # Never trust client-supplied user_id when auth is enabled.
    effective_user = auth.subject if auth.auth_type != "none" else header_user_id
    effective_payload = payload.model_copy(update={"user_id": effective_user})

    await container.rate_limiter.enforce(effective_user)
    return await container.review_service.review_code(effective_payload)


@router.post("/batch", response_model=BatchReviewResponse)
async def create_batch_review(
    payload: BatchReviewRequest,
    container: Annotated[ServiceContainer, Depends(get_container)],
    header_user_id: Annotated[str, Depends(get_user_id)],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> BatchReviewResponse:
    effective_user = auth.subject if auth.auth_type != "none" else header_user_id
    items = [item.model_copy(update={"user_id": effective_user}) for item in payload.items]
    await container.rate_limiter.enforce(effective_user)
    return await container.review_service.review_batch(items)


@router.get("/history", response_model=list[ReviewHistoryItem])
async def get_review_history(
    container: Annotated[ServiceContainer, Depends(get_container)],
    auth: Annotated[AuthContext, Depends(require_auth)],
    user_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ReviewHistoryItem]:
    if auth.auth_type != "none":
        # Prevent querying other users' history when auth is enabled.
        user_id = auth.subject
    return await container.review_service.get_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    container: Annotated[ServiceContainer, Depends(get_container)],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> ReviewResponse:
    """Get a specific review by ID with rate limiting.
    
    Args:
        review_id: The review identifier
        container: Service container
        auth: Authentication context
        
    Returns:
        ReviewResponse: The stored review result
        
    Raises:
        HTTPException: If review not found (404) or rate limited (429)
    """
    # Validate review_id format (should be UUID-like)
    if not review_id or len(review_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review_id format.",
        )
    
    # Apply rate limiting even on GET requests
    user_id = auth.subject if auth.auth_type != "none" else "anonymous"
    await container.rate_limiter.enforce(user_id)
    
    record = await container.review_service.get_review(review_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' was not found.",
        )
    return record
