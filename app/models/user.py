from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from beanie import Document
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    DISABLED = "disabled"


class OtpInfo(BaseModel):
    code: str
    expires_at: datetime
    attempts: int = 0
    resend_count: int = 0
    resend_window_start: datetime | None = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    organization_id: str | None = None


class UserCreate(UserBase):
    password: str


class User(Document, UserBase):
    id: UUID = Field(default_factory=uuid4)
    hashed_password: str
    device_token: str | None = None
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    otp: OtpInfo | None = None
    roles: list[str] = []
    tenant_ids: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        # Email should be unique at DB level (create unique index).
        unique_indexes = [
            [("email", 1)],
        ]

    model_config = ConfigDict(populate_by_name=True)


class UserPublic(BaseModel):
    id: str | None = None
    email: EmailStr
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    organization_id: str | None = None
    status: UserStatus | None = None
    roles: list[str] = []
    tenant_ids: list[str] = []
