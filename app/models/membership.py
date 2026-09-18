from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Membership(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    organization_id: UUID
    role: str = Field(default="worker")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "memberships"

    model_config = ConfigDict(populate_by_name=True)
