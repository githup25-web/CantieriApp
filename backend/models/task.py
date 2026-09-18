from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, UUID4

from backend.models.user import PyObjectId

TaskStatus = Literal["todo", "in_progress", "done"]
StatoTask = Literal["in_attesa", "in_corso", "completato"]


class Task(BaseModel):
    """Documento MongoDB per un task di cantiere."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    cantiere_id: str = Field(min_length=1)
    titolo: str = Field(min_length=1, max_length=200)
    descrizione: str = Field(min_length=1, max_length=5000)
    assegnato_a: str = Field(min_length=1)
    stato: StatoTask = "in_attesa"
    data_creazione: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data_scadenza: datetime | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class TaskDB(BaseModel):
    """Documento MongoDB per un task isolato per tenant."""

    id: UUID4 = Field(default_factory=uuid4, alias="_id")
    tenant_id: UUID = Field(alias="tenantId")
    title: str
    description: str
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")
    status: TaskStatus = "todo"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str},
    )
