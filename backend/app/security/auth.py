from dataclasses import dataclass

import jwt


@dataclass
class AuthContext:
    auth_type: str
    subject: str | None = None


def authenticate_request(
    *,
    auth_mode: str,
    auth_api_keys: str,
    authorization: str | None,
    x_api_key: str | None,
    jwt_secret: str,
    jwt_algorithm: str,
    jwt_audience: str | None,
    jwt_issuer: str | None,
) -> AuthContext:
    mode = auth_mode.strip().lower()
    if mode in {"", "none", "off", "disabled"}:
        return AuthContext(auth_type="none")

    allow_api_key = mode in {"api_key", "both"}
    allow_jwt = mode in {"jwt", "both"}

    if allow_api_key and x_api_key:
        keys = {item.strip() for item in auth_api_keys.split(",") if item.strip()}
        if x_api_key in keys:
            return AuthContext(auth_type="api_key", subject="api-key-user")

    if allow_jwt and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        decode_kwargs: dict[str, str] = {}
        if jwt_audience:
            decode_kwargs["audience"] = jwt_audience
        if jwt_issuer:
            decode_kwargs["issuer"] = jwt_issuer

        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            **decode_kwargs,
        )
        return AuthContext(auth_type="jwt", subject=str(payload.get("sub", "unknown")))

    raise jwt.InvalidTokenError("Request is missing valid authentication credentials.")
