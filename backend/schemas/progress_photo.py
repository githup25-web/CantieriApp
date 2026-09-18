from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProgressPhotoCreateSchema(BaseModel):
    """Payload per associare una foto di avanzamento a un task."""

    task_id: UUID = Field(alias="taskId")
    url: str = Field(min_length=1, max_length=2048)

    model_config = ConfigDict(populate_by_name=True)


class ProgressPhotoResponseSchema(BaseModel):
    """Rappresentazione pubblica di una foto di avanzamento."""

    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    task_id: UUID = Field(alias="taskId")
    user_id: UUID = Field(alias="userId")
    url: str
    created_at: str = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)