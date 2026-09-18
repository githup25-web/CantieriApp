from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import PyObjectId


class FotoAvanzamentoCreateSchema(BaseModel):
    """Payload per registrare una foto di avanzamento."""

    cantiere_id: str = Field(min_length=1)
    worker_id: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2048)
    descrizione: str | None = Field(default=None, max_length=5000)


class FotoAvanzamentoResponseSchema(BaseModel):
    """Rappresentazione JSON-compatible di una foto di avanzamento MongoDB."""

    id: PyObjectId = Field(alias="_id")
    cantiere_id: str
    worker_id: str
    url: str
    timestamp: datetime
    descrizione: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )