from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID, uuid4

from beanie import Document
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Invite(Document):
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr
    role: str
    organization_id: UUID
    token: str = Field(default_factory=lambda: token_urlsafe(24))
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=72))

    class Settings:
        name = "invites"

    model_config = ConfigDict(populate_by_name=True)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
