from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


class Presence(Document):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    organization_id: UUID
    cantiere_id: UUID
    type: str
    gps_lat: float
    gps_lon: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = None
    weather: str | None = None

    class Settings:
        name = "presences"
        indexes = [
            ["user_id", "cantiere_id"],
        ]

    model_config = ConfigDict(populate_by_name=True)
