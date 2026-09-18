from __future__ import annotations

from datetime import datetime, timedelta

from app.models.event_queue import EventQueue
from app.models.event_record import EventRecord


async def retry_failed_events():
    """
    Retry logic ONLY.

    Rules:
    - find events in EventQueue with state="error"
    - for each: increment attempts
      - if attempts <= 5 -> state="pending"
      - if attempts > 5  -> state="failed"
    - save each event
    - NON: dispatch / process_event / fetch_pending_event
    """
    cursor = EventQueue.find(EventQueue.state == "error")

    async for event in cursor:
        event.attempts = int(event.attempts or 0) + 1

        if event.attempts <= 5:
            event.state = "pending"
            event.last_error = None
        else:
            event.state = "failed"

        await event.save()


async def cleanup_old_events(days: int = 30):
    """
    Cleanup ONLY.

    Deletes historical EventRecord documents older than X days.
    - cancella EventRecord con occurred_at più vecchio di X giorni
    - usa datetime.utcnow() - timedelta(days)
    - NON toccare EventQueue
    - questa funzione pulisce solo i record storici
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    cursor = EventRecord.find(EventRecord.occurred_at < cutoff)

    async for record in cursor:
        await record.delete()
