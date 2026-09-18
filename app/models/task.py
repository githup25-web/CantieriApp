from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Task(Document):
    id: UUID = Field(default_factory=uuid4)
    cantiere_id: UUID
    organization_id: UUID
    title: str
    description: str
    assigned_to: UUID | None = None
    status: str = "todo"
    progress: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"
        indexes = [["cantiere_id"]]

    model_config = ConfigDict(populate_by_name=True)
