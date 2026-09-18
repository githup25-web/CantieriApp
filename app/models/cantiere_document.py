from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class CantiereDocument(Document):
    id: UUID = Field(default_factory=uuid4)
    cantiere_id: UUID
    organization_id: UUID
    user_id: UUID
    type: str
    title: str
    description: str | None = None
    url: str
    # size (KB) for client display; optional for backward compatibility.
    size_kb: int | None = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    class Settings:
        name = "cantiere_documents"
        indexes = [["cantiere_id"]]

    model_config = ConfigDict(populate_by_name=True)
