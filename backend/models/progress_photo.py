from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, UUID4


class ProgressPhotoDB(BaseModel):
    """Documento MongoDB di una foto di avanzamento associata a un task."""

    id: UUID4 = Field(default_factory=uuid4, alias="_id")
    tenant_id: UUID = Field(alias="tenantId")
    task_id: UUID = Field(alias="taskId")
    user_id: UUID = Field(alias="userId")
    url: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str},
    )
