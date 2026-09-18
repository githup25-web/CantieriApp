from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, UUID4


class PresenceDB(BaseModel):
    """Documento MongoDB della presenza giornaliera di un utente."""

    id: UUID4 = Field(default_factory=uuid4, alias="_id")
    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID = Field(alias="userId")
    attendance_date: str = Field(alias="date")
    check_in: datetime | None = Field(default=None, alias="checkIn")
    check_out: datetime | None = Field(default=None, alias="checkOut")
    notes: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={UUID: str},
    )

    @classmethod
    def for_check_in(
        cls,
        *,
        tenant_id: UUID,
        user_id: UUID,
        notes: str | None = None,
    ) -> "PresenceDB":
        now = datetime.now(timezone.utc)
        return cls(
            tenantId=tenant_id,
            userId=user_id,
            date=now.date().isoformat(),
            checkIn=now,
            notes=notes,
        )
