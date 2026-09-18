from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document
from pydantic import ConfigDict, Field


class DeadLetter(Document):
    event_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)

    attempts: int
    last_error: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "dead_letter"

    model_config = ConfigDict(populate_by_name=True)
