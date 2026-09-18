from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from beanie import Document
from pydantic import ConfigDict, Field


class EventRecord(Document):

    # Domain event name (e.g. "fattura.created")
    event_name: str

    # Best-effort event payload to rehydrate context for consumers
    payload: dict[str, Any] = Field(default_factory=dict)

    # When the event occurred (producer-time)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Stable identifier for idempotency at the event level
    # Must be unique in the collection.
    event_instance_id: str

    class Settings:
        name = "event_records"
        indexes = [
            [("event_instance_id", 1)],
        ]

    model_config = ConfigDict(populate_by_name=True)
