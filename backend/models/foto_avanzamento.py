from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import PyObjectId


class FotoAvanzamento(BaseModel):
    """Documento MongoDB per una foto di avanzamento lavori."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    cantiere_id: str = Field(min_length=1)
    worker_id: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2048)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    descrizione: str | None = Field(default=None, max_length=5000)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )