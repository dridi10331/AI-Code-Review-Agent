from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from jwt import InvalidTokenError

from backend.app.core.config import Settings, get_settings
from backend.app.core.container import ServiceContainer
from backend.app.security.auth import AuthContext, authenticate_request


def get_app_settings() -> Settings:
    return get_settings()


def get_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application services are not initialized.",
        )
    return container


def get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    return x_user_id or "anonymous"


def require_auth(
    settings: Annotated[Settings, Depends(get_app_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> AuthContext:
    try:
        return authenticate_request(
            auth_mode=settings.auth_mode,
            auth_api_keys=settings.auth_api_keys,
            authorization=authorization,
            x_api_key=x_api_key,
            jwt_secret=settings.jwt_secret,
            jwt_algorithm=settings.jwt_algorithm,
            jwt_audience=settings.jwt_audience,
            jwt_issuer=settings.jwt_issuer,
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
