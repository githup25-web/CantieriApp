from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    """Schema for creating a new tenant/organization."""
    name: str
    slug: str
    description: str | None = None


class TenantUpdate(BaseModel):
    """Schema for partial tenant update."""
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TenantDB(BaseModel):
    """MongoDB document structure for tenants collection (FASE 2).

    Fields use snake_case in Python but map to camelCase in MongoDB.
    Includes automatic createdAt/updatedAt timestamps.
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str, ObjectId: str},
    )


class TenantPublic(BaseModel):
    """Public tenant data returned by API."""
    id: str
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True


class MembershipCreate(BaseModel):
    """Schema for creating a new membership."""
    user_id: UUID
    tenant_id: UUID
    role: str = "worker"


class MembershipDB(BaseModel):
    """MongoDB document structure for memberships collection (FASE 2).

    Links a user to a tenant with a specific role.
    Includes tenantId for multi-tenant document isolation.
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID = Field(alias="userId")
    tenant_id: UUID = Field(alias="tenantId")
    role: str = "worker"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str, ObjectId: str},
    )


class MembershipResponse(BaseModel):
    """Membership data returned by API."""
    user_id: str
    tenant_id: str
    role: str
    user_email: str | None = None
