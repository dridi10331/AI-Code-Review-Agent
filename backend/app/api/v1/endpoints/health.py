from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_app_settings, get_container
from backend.app.core.config import Settings
from backend.app.core.container import ServiceContainer
from backend.app.models.review import HealthStatus

router = APIRouter(prefix="")


@router.get("/health", response_model=HealthStatus)
async def healthcheck(
    container: Annotated[ServiceContainer, Depends(get_container)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> HealthStatus:
    redis_ok = False
    database_ok = False

    try:
        redis_ok = bool(await container.redis.ping())
    except Exception:
        redis_ok = False

    try:
        await container.repository.list_history(user_id=None, limit=1, offset=0)
        database_ok = True
    except Exception:
        database_ok = False

    return HealthStatus(
        status="ok" if redis_ok and database_ok else "degraded",
        redis=redis_ok,
        database=database_ok,
        environment=settings.environment,
    )
