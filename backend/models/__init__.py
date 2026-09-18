"""Pydantic models for MongoDB documents (FASE 2).

All models use Pydantic v2 with:
- UUID4 for document IDs
- camelCase aliases for MongoDB field mapping
- Automatic createdAt/updatedAt timestamps
- tenantId field for multi-tenant document isolation
- PyObjectId serializer for ObjectId compatibility
"""

from backend.models.user import (
    PyObjectId,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserDB,
    UserPublic,
    UserInDB,
    TokenResponse,
)

from backend.models.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantDB,
    TenantPublic,
    MembershipCreate,
    MembershipDB,
    MembershipResponse,
)

__all__ = [
    # User models
    "PyObjectId",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserDB",
    "UserPublic",
    "UserInDB",
    "TokenResponse",
    # Tenant models
    "TenantCreate",
    "TenantUpdate",
    "TenantDB",
    "TenantPublic",
    "MembershipCreate",
    "MembershipDB",
    "MembershipResponse",
]
