"""Schemi Pydantic v2 per il sistema di inviti (FASE 5).

Convenzioni:
- snake_case nei modelli Python
- camelCase nei documenti MongoDB (via alias)
- RLS: ogni invito è legato a un tenantId
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class InviteCreateSchema(BaseModel):
    """Schema per la creazione di un invito (solo admin/owner)."""

    email: EmailStr
    role: str
    full_name: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Il ruolo deve essere worker o client."""
        if v not in ("worker", "client"):
            raise ValueError("Il ruolo deve essere 'worker' o 'client'")
        return v


class InviteAcceptSchema(BaseModel):
    """Schema per l'accettazione di un invito (endpoint pubblico)."""

    token: str
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class InviteResponseSchema(BaseModel):
    """Risposta API per un invito."""

    id: str
    email: str
    role: str
    token: str
    status: str
    tenant_id: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_by: str | None = None
    canceled_at: datetime | None = None


class InviteListResponseSchema(BaseModel):
    """Risposta API per la lista di inviti."""

    items: list[InviteResponseSchema]
    total: int
