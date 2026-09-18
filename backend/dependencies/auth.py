from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.core.database import get_collection
from backend.core.jwt import verify_token
from backend.models.user import UserInDB

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> UserInDB:
    """Dependency that extracts and validates the current authenticated user.

    Decodes the JWT access token, fetches the user from MongoDB,
    enforces that the user is active, and returns a UserInDB instance.

    Raises:
        HTTPException 401: If no credentials, invalid token, or user not found.
        HTTPException 403: If the user account is inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_token(credentials.credentials, expected_type="access")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Invalid or expired token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    users_collection = get_collection("users")
    user_doc = await users_collection.find_one({"_id": UUID(user_id)})

    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return UserInDB(**user_doc)


async def get_current_tenant(
    current_user: UserInDB = Depends(get_current_user),
) -> dict:
    """Dependency that returns the tenant document for the current user.

    Uses the tenantId from the authenticated user to fetch the
    corresponding tenant document from MongoDB.

    Raises:
        HTTPException 404: If the tenant is not found.
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no tenant assigned",
        )

    tenants_collection = get_collection("tenants")
    tenant_doc = await tenants_collection.find_one(
        {"_id": UUID(current_user.tenant_id)}
    )

    if tenant_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant_doc
