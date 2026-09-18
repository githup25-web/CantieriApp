from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import ConfigDict, Field


class EventQueue(Document):

    event_instance_id: str
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: str = Field(default="pending")  # pending | processing | done | error

    attempts: int = 0
    last_error: str | None = None

    next_attempt_at: datetime | None = None
    max_attempts: int = 5

    class Settings:
        name = "event_queue"
        indexes = [
            [("event_instance_id", 1)],
            [("state", 1), ("occurred_at", -1)],
            [("state", 1), ("next_attempt_at", 1)],
        ]

    model_config = ConfigDict(populate_by_name=True)
