from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Cantiere(Document):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID

    title: str
    description: str | None = None

    assigned_worker_id: UUID | None = None
    status: str = "planned"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "cantieri"
        indexes = [["organization_id"], ["status"]]

    model_config = ConfigDict(populate_by_name=True)
