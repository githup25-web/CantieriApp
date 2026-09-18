from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


class Expense(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    organization_id: UUID
    cantiere_id: UUID
    category: str
    amount: float
    description: str
    receipt_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "expenses"
        indexes = [
            ["user_id", "cantiere_id"],
        ]

    model_config = ConfigDict(populate_by_name=True)
