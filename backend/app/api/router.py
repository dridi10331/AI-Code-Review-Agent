from fastapi import APIRouter, Depends

from backend.app.api.deps import require_auth
from backend.app.api.v1.endpoints import health, reviews, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

protected_router = APIRouter(dependencies=[Depends(require_auth)])
protected_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])

api_router.include_router(protected_router)
