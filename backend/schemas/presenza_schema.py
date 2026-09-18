from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import PyObjectId


class PresenzaCreateSchema(BaseModel):
    """Payload per il check-in di un worker."""

    worker_id: str = Field(min_length=1)
    cantiere_id: str = Field(min_length=1)
    checkin: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PresenzaCheckoutSchema(BaseModel):
    """Payload per il checkout della presenza aperta di un worker in un cantiere."""

    worker_id: str = Field(min_length=1)
    cantiere_id: str = Field(min_length=1)
    checkout: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PresenzaResponseSchema(BaseModel):
    """Rappresentazione JSON-compatible di una presenza MongoDB."""

    id: PyObjectId = Field(alias="_id")
    worker_id: str
    cantiere_id: str
    checkin: datetime
    checkout: datetime | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )