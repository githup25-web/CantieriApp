from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.event_queue import EventQueue


async def mark_completed(event_id: str) -> None:
    """
    Update EventQueue state to "done" for the given event_instance_id.

    Rules:
    - this file ONLY manages state
    - does NOT dispatch or fetch
    """
    event = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if event is None:
        return

    event.state = "done"

    # Some schemas may not define completed_at; set it only if present.
    if hasattr(event, "completed_at"):
        setattr(event, "completed_at", datetime.utcnow())

    await event.save()


async def mark_failed(event_id: str, error: Any) -> None:
    """
    Update EventQueue state to "error" for the given event_instance_id.

    Rules:
    - this file ONLY manages state
    - does NOT dispatch or fetch
    """
    event = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if event is None:
        return

    event.state = "error"
    event.attempts = int(event.attempts or 0) + 1
    event.last_error = str(error)

    await event.save()


async def increment_retry(event_id: str) -> None:
    """
    Increment EventQueue attempts for the given event_instance_id.

    If attempts exceed 5, mark the event as failed.

    Rules:
    - this file ONLY manages state
    - does NOT dispatch or fetch
    """
    event = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if event is None:
        return

    event.attempts = int(event.attempts or 0) + 1

    if event.attempts > 5:
        event.state = "failed"

    await event.save()
