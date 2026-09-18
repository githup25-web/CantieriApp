from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PresenceCheckInSchema(BaseModel):
    """Payload opzionale per il check-in giornaliero."""

    notes: str | None = Field(default=None, max_length=2000)


class PresenceCheckOutSchema(BaseModel):
    """Payload opzionale per il check-out giornaliero."""

    notes: str | None = Field(default=None, max_length=2000)


class PresenceResponseSchema(BaseModel):
    """Rappresentazione pubblica di una presenza giornaliera."""

    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID = Field(alias="userId")
    date: str
    check_in: str | None = Field(default=None, alias="checkIn")
    check_out: str | None = Field(default=None, alias="checkOut")
    notes: str | None = None

    model_config = ConfigDict(populate_by_name=True)