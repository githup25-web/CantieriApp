from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Fattura(Document):
    id: UUID = Field(default_factory=uuid4)
    cantiere_id: UUID
    organization_id: UUID
    user_id: UUID

    number: str  # es: FAT-2026-001
    description: str | None = None
    amount: float

    status: str = "emessa"  # emessa, pagata, scaduta
    pdf_url: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "fatture"
        indexes = [["cantiere_id"], ["organization_id", "cantiere_id"]]

    model_config = ConfigDict(populate_by_name=True)
