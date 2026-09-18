from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import PyObjectId


class Presenza(BaseModel):
    """Documento MongoDB per la presenza di un worker in un cantiere."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    worker_id: str = Field(min_length=1)
    cantiere_id: str = Field(min_length=1)
    checkin: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checkout: datetime | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )