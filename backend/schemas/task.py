from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.task import TaskStatus


class TaskCreateSchema(BaseModel):
    """Payload per la creazione di un task da parte di un admin."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")

    model_config = ConfigDict(populate_by_name=True)


class TaskUpdateSchema(BaseModel):
    """Payload parziale per l'aggiornamento di un task."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")
    status: TaskStatus | None = None

    model_config = ConfigDict(populate_by_name=True)


class TaskResponseSchema(BaseModel):
    """Rappresentazione pubblica di un task."""

    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    title: str
    description: str
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")
    status: TaskStatus
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)