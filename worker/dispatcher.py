from __future__ import annotations

from app.models.event_queue import EventQueue

from worker.fetcher import fetch_pending_event
from worker.processor import process_event


async def dispatch_next_event() -> None:
    """
    Orchestrates dispatch ONLY.

    Steps:
    1) uses fetch_pending_event()
    2) if no events -> return
    3) sets event.state = "processing" and saves
    4) delegates actual work to process_event(event)
    """
    event = await fetch_pending_event()
    if event is None:
        return

    # Per richiesta esplicita del Prompt 9, imponiamo e salviamo lo stato
    event.state = "processing"
    if isinstance(event, EventQueue):
        await event.save()
    else:
        # Safety fallback: if fetcher returns a compatible object, try to save anyway.
