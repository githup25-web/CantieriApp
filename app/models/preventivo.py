from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Preventivo(Document):
    id: UUID = Field(default_factory=uuid4)
    cantiere_id: UUID
    organization_id: UUID
    user_id: UUID

    title: str
    description: str | None = None
    amount: float

    status: str = "bozza"  # bozza, inviato, approvato, rifiutato
    pdf_url: str | None = None

    version: int = 1

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "preventivi"
        indexes = [["cantiere_id"], ["organization_id", "cantiere_id"]]

    model_config = ConfigDict(populate_by_name=True)
