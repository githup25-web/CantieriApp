from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.event_queue import EventQueue
from app.models.event_record import EventRecord


async def process_event(event: EventQueue) -> None:
    """
    Process a single event already in state="processing".

    Rules:
    - business logic: placeholder/mock (no reale dispatch)
    - on success -> event.state="done"
    - on error   -> event.state="error" and increment event.attempts
    - save event
    - create EventRecord with:
      - event_instance_id = event.id
      - occurred_at = datetime.utcnow()
      - state = event.state
    - NON: dispatch, NON: retry, NON: cleanup
    """
    try:
        # Placeholder business logic (mock/no-op)
        # (If you need additional checks, add them here without dispatching.)
        _ = getattr(event, "event_name", None)
        _ = getattr(event, "payload", None)

        event.state = "done"

    except Exception:
        event.state = "error"
        event.attempts = int(event.attempts or 0) + 1

    # persist event state
    await event.save()

    # create historical record
    record = EventRecord(
        event_instance_id=str(event.id),
        occurred_at=datetime.utcnow(),
        state=event.state,  # type: ignore[arg-type]
    )

    await record.insert()
