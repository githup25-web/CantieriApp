"""Modelli Pydantic per il sistema di inviti (FASE 5).

Convenzioni:
- snake_case nei modelli Python
- camelCase nei documenti MongoDB (via alias)
- RLS: ogni query è filtrata per tenantId
- Token invito generato con UUID4
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InviteCreate(BaseModel):
    """Schema per la creazione di un nuovo invito.

    L'admin crea l'invito specificando email e ruolo
    (worker per WorkerApp, client per ClienteApp).
    """

    email: EmailStr
    role: str  # "worker" | "client"
    full_name: str | None = None


class InviteAccept(BaseModel):
    """Schema per l'accettazione di un invito (endpoint pubblico)."""

    token: str
    full_name: str
    password: str


class InviteDB(BaseModel):
    """Documento MongoDB per la collection `invites` (FASE 5).

    Campi MongoDB (camelCase):
    - _id: UUID
    - email: str
    - role: str (worker | client)
    - token: str (UUID4)
    - status: str (pending | accepted | canceled | expired)
    - tenantId: UUID (RLS)
    - createdBy: UUID (admin che ha creato l'invito)
    - createdAt: datetime
    - expiresAt: datetime (default 72h)
    - acceptedAt: datetime | None
    - acceptedBy: UUID | None
    - canceledAt: datetime | None
    - updatedAt: datetime
    """

    id: UUID = Field(default_factory=uuid4, alias="_id")
    email: str
    role: str
    token: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "pending"  # pending | accepted | canceled | expired
    tenant_id: UUID = Field(alias="tenantId")
    created_by: UUID = Field(alias="createdBy")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=72),
        alias="expiresAt",
    )
    accepted_at: datetime | None = Field(default=None, alias="acceptedAt")
    accepted_by: UUID | None = Field(default=None, alias="acceptedBy")
    canceled_at: datetime | None = Field(default=None, alias="canceledAt")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str},
        from_attributes=True,
    )

    def is_expired(self) -> bool:
        """Verifica se l'invito è scaduto.

        MongoDB restituisce datetime naive (senza timezone);
        normalizziamo il timezone a UTC prima del confronto.
        """
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at


class InvitePublic(BaseModel):
    """Dati pubblici di un invito restituiti dall'API."""

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
