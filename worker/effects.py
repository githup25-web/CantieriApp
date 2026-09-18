from __future__ import annotations

from app.models.event_record import EventRecord


async def apply_effects(event) -> None:
    """
    Post-processing effects for a processed event.

    Rules:
    - persist only (no state update, no dispatch)
    - create an EventRecord mirroring the producer event context
    """
    record = EventRecord(
        event_instance_id=event.event_instance_id,
        event_name=event.event_name,
        payload=event.payload,
        occurred_at=event.occurred_at,
    )

    await record.insert()
