from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.models.task import StatoTask
from backend.models.user import PyObjectId


class TaskCreateSchema(BaseModel):
    """Payload per la creazione di un task."""

    cantiere_id: str = Field(min_length=1)
    titolo: str = Field(min_length=1, max_length=200)
    descrizione: str = Field(min_length=1, max_length=5000)
    assegnato_a: str = Field(min_length=1)
    stato: StatoTask = "in_attesa"
    data_scadenza: datetime | None = None


class TaskUpdateSchema(BaseModel):
    """Payload parziale per l'aggiornamento di un task."""

    titolo: str | None = Field(default=None, min_length=1, max_length=200)
    descrizione: str | None = Field(default=None, min_length=1, max_length=5000)
    assegnato_a: str | None = Field(default=None, min_length=1)
    stato: StatoTask | None = None
    data_scadenza: datetime | None = None


class TaskResponseSchema(BaseModel):
    """Rappresentazione JSON-compatible di un task MongoDB."""

    id: PyObjectId = Field(alias="_id")
    cantiere_id: str
    titolo: str
    descrizione: str
    assegnato_a: str
    stato: StatoTask
    data_creazione: datetime
    data_scadenza: datetime | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )