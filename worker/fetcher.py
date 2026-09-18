from __future__ import annotations

from app.models.event_queue import EventQueue


async def fetch_pending_event() -> EventQueue | None:
    """
    Prende atomically un evento con state="pending", ordinandolo per occurred_at crescente,
    e lo aggiorna a state="processing".

    Ritorna l'evento trovato (dopo update) oppure None.
    """
    # Nota: usiamo find_one_and_update per garantire l'atomicità del passaggio pending -> processing
    # nello stesso comando di fetch/update.
    return await EventQueue.find_one_and_update(
        EventQueue.state == "pending",
        {"$set": {"state": "processing"}},
        sort=[("occurred_at", 1)],
        return_document=True,
    )
