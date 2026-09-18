from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from backend.core.config import get_settings

settings = get_settings()


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with multi‑tenant claims.

    Args:
        user_id: The user's UUID as string.
        tenant_id: The tenant's UUID as string.
        role: The user's role within the tenant (e.g. 'admin', 'worker').
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": user_id,
        "tenantId": tenant_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: The user's UUID as string.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT string to verify.
        expected_type: Expected token type ('access' or 'refresh').

    Returns:
        Decoded payload dictionary.

    Raises:
        JWTError: If the token is invalid, expired, or has wrong type.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    token_type = payload.get("type")
    if token_type != expected_type:
        raise JWTError(f"Invalid token type: expected '{expected_type}', got '{token_type}'")

    return payload
