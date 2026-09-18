from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class ProgressPhoto(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    organization_id: UUID
    cantiere_id: UUID
    stage: str
    url: str
    description: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "progress_photos"
        indexes = [
            ["cantiere_id"],
        ]

    model_config = ConfigDict(populate_by_name=True)
