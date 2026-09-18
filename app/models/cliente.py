from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import ConfigDict, Field


def generate_cliente_code() -> str:
    """Genera un codice cliente univoco nel formato CANT-XXXXXX."""
    digits = random.randint(0, 999999)
    return f"CANT-{digits:06d}"


class Cliente(Document):
    """Cliente registrato nel sistema (FASE 7)."""

    id: UUID = Field(default_factory=uuid4)
    code: str = Field(default_factory=generate_cliente_code)
    full_name: str
    tenant_id: UUID
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "clienti"
        indexes = [
            [("code", 1)],
            [("tenant_id", 1)],
        ]

    model_config = ConfigDict(populate_by_name=True)
