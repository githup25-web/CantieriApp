from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from app.core.events import dispatcher
from app.core.events_contract import normalize_event_context


def _ensure_event_instance_id(payload: dict[str, Any]) -> dict[str, Any]:
    ctx = dict(payload or {})
    if not ctx.get("event_instance_id"):
        ctx["event_instance_id"] = str(uuid.uuid4())
    return ctx


async def _best_effort_persist_and_enqueue(*, event_name: str, ctx: dict[str, Any], normalized: dict[str, Any]) -> None:
    """
    Best-effort event persistence + enqueue.

    Requirements:
    - Never crash routers/endpoints.
    - Idempotent on event_instance_id at EventRecord level.
    - Idempotent enqueue as well (avoid duplicates).
    - Works even if FastAPI startup (Beanie init) hasn't run yet.
    """
    try:
        # Lazy imports so event_bus works in scripts/tests even without FastAPI startup.
        from app.models.event_record import EventRecord
        from app.models.event_queue import EventQueue

        event_instance_id = str(ctx.get("event_instance_id") or normalized.get("event_instance_id"))
        if not event_instance_id:
            return

        # Persist EventRecord (idempotent on event_instance_id).
        try:
            occurred_at = normalized.get("occurred_at")
            # Be defensive: occurred_at should be a datetime, but we don't want typing/None issues.
            from datetime import datetime, timezone
            if not isinstance(occurred_at, datetime):
                occurred_at = datetime.now(timezone.utc)

            rec = EventRecord(
                event_name=event_name,
                payload=ctx,  # keep producer/normalized context for rehydration/debug
                occurred_at=occurred_at,
                event_instance_id=event_instance_id,
            )
            await rec.insert()
        except Exception:
            # Duplicate or transient failure => treat as idempotent/ok.
            pass

        # Enqueue (idempotent on event_instance_id).
        try:
            exists = await EventQueue.find_one(EventQueue.event_instance_id == event_instance_id)
            if exists is None:
                item = EventQueue(
                    event_instance_id=event_instance_id,
                    event_name=event_name,
                    payload=ctx,
                    state="pending",
                )
                await item.insert()
        except Exception:
            # Enqueue failures must not impact request path.
            pass
    except Exception:
        # Beanie not initialized / collections not ready / any other transient failure.
        pass


async def emit_event(*, event_name: str, payload: dict[str, Any]) -> None:
    """
    Main entrypoint for emitting domain events from the backend.

    - Ensures event_instance_id exists (for idempotency).
    - Normalizes payload to the legacy/official dispatcher context contract.
    - Persists + enqueues (best-effort).
    - Dispatches via app.core.events.dispatcher.
    """
    ctx = _ensure_event_instance_id(payload)
    normalized = normalize_event_context(event_name, ctx)

    await _best_effort_persist_and_enqueue(event_name=event_name, ctx=ctx, normalized=normalized)

    await dispatcher.dispatch(event_name, normalized)
