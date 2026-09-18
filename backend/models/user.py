from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId serialization with Pydantic v2."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _validation_info=None):
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator, _field_schema):
        return {"type": "string"}


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for partial user update."""
    full_name: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    device_token: str | None = None
    tenant_id: str | None = None


class UserDB(BaseModel):
    """MongoDB document structure for users collection (FASE 2).

    Fields use snake_case in Python but map to camelCase in MongoDB.
    Every document includes tenantId for multi-tenant support.
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    email: str
    hashed_password: str
    full_name: str | None = None
    tenant_id: str | None = Field(default=None, alias="tenantId")
    is_active: bool = True
    is_superuser: bool = False
    device_token: str | None = None
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


class UserPublic(BaseModel):
    """Public user data returned by API."""
    id: str
    email: str
    full_name: str | None = None
    tenant_id: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInDB(BaseModel):
    """Internal user representation with hashed password.

    Used for direct MongoDB document mapping with camelCase aliases.
    """
    id: UUID = Field(alias="_id")
    email: str
    hashed_password: str
    full_name: str | None = None
    tenant_id: str | None = Field(default=None, alias="tenantId")
    is_active: bool = True
    is_superuser: bool = False
    device_token: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str, ObjectId: str},
    )
