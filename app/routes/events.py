from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from beanie.operators import In
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.dead_letter import DeadLetter
from app.models.event_queue import EventQueue
from app.models.event_record import EventRecord

router = APIRouter(prefix="/events", tags=["events"])


class PushEventIn(BaseModel):
    event_type: str
    payload: dict[str, Any]


class FailEventIn(BaseModel):
    reason: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowStartIn(BaseModel):
    name: str
    context: dict[str, Any] = Field(default_factory=dict)

@router.post("/workflow/start")
async def start_workflow_endpoint(body: WorkflowStartIn) -> dict[str, str]:
    ev = EventQueue(
        event_instance_id=f"wfstart_{datetime.now(timezone.utc).timestamp()}".replace(".", "_"),
        event_name="workflow.start",
        payload={"name": body.name, "context": body.context or {}},
        occurred_at=_utc_now(),
        state="pending",
        attempts=0,
        last_error=None,
        next_attempt_at=None,
        max_attempts=5,
    )
    await ev.insert()
    return {"status": "queued", "workflow": body.name}


@router.post("/push")
async def push_event(body: PushEventIn) -> dict[str, str]:
    # Create a stable event_instance_id for idempotency at this layer.
    event_instance_id = f"evt_{datetime.now(timezone.utc).timestamp()}".replace(".", "_")

    event = EventQueue(
        event_instance_id=event_instance_id,
        event_name=body.event_type,
        payload=body.payload,
        occurred_at=_utc_now(),
        state="pending",
        attempts=0,
        last_error=None,
        next_attempt_at=None,
        max_attempts=5,
    )
    await event.insert()

    # Also store an EventRecord for potential future rehydration/consumers.
    record = EventRecord(
        event_instance_id=event_instance_id,
        event_name=body.event_type,
        payload=body.payload,
        occurred_at=event.occurred_at,
    )
    await record.insert()

    return {"status": "queued", "event_id": event_instance_id}


@router.get("/fetch/{worker_id}")
async def fetch_event(worker_id: str) -> dict[str, Any] | None:
    now = _utc_now()

    # Avoid Beanie operator "<=" with Optional[datetime] by filtering in Python.
    due_without_next = await (
        EventQueue.find((EventQueue.state == "pending") & (EventQueue.next_attempt_at == None))  # noqa: E711
        .sort("occurred_at")
        .limit(1)
        .to_list()
    )

    pending_with_next = await (
        EventQueue.find((EventQueue.state == "pending") & (EventQueue.next_attempt_at != None))  # noqa: E711
        .sort("occurred_at")
        .to_list()
    )

    candidate = due_without_next[0] if due_without_next else None

    # Pick the earliest occurred_at among due events with next_attempt_at set.
    for ev in pending_with_next:
        if ev.next_attempt_at is not None and ev.next_attempt_at <= now:
            if candidate is None or ev.occurred_at < candidate.occurred_at:
                candidate = ev
            break

    if candidate is None:
        return None

    ev = candidate
    ev.state = "processing"
    ev.attempts = (ev.attempts or 0) + 1
    await ev.save()

    return {
        "event_id": ev.event_instance_id,
        "event_type": ev.event_name,
        "event_name": ev.event_name,
        "payload": ev.payload,
        "attempts": ev.attempts,
        "max_attempts": ev.max_attempts,
        "next_attempt_at": ev.next_attempt_at,
    }


@router.post("/ack/{event_id}")
async def ack(event_id: str) -> dict[str, str]:
    item = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if item is None:
        raise HTTPException(status_code=404, detail="event not found")
    item.state = "done"
    item.last_error = None
    await item.save()
    return {"status": "acknowledged"}


@router.post("/fail/{event_id}")
async def fail(event_id: str, body: FailEventIn) -> dict[str, str]:
    now = _utc_now()

    item = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if item is None:
        raise HTTPException(status_code=404, detail="event not found")

    # Retry bookkeeping
    item.attempts = (item.attempts or 0) + 1
    item.last_error = body.reason[:2000]

    from datetime import timedelta

    backoff_seconds = 2 ** int(item.attempts)
    item.next_attempt_at = now + timedelta(seconds=backoff_seconds)

    # DLQ decision
    if int(item.attempts) >= int(item.max_attempts or 5):
        dlq = DeadLetter(
            event_id=item.event_instance_id,
            event_type=item.event_name,
            payload=item.payload,
            attempts=item.attempts,
            last_error=item.last_error or "",
            failed_at=now,
        )
        await dlq.insert()

        # Move out of the processing queue: do not return again on fetch.
        item.state = "error"
        item.next_attempt_at = None
        await item.save()
        return {"status": "dead_letter", "attempts": str(item.attempts)}

    # Keep it pending for future retry.
    item.state = "pending"
    await item.save()
    return {"status": "failed_retry", "attempts": str(item.attempts)}


@router.post("/requeue/{event_id}")
async def requeue(event_id: str) -> dict[str, str]:
    item = await EventQueue.find_one(EventQueue.event_instance_id == event_id)
    if item is None:
        raise HTTPException(status_code=404, detail="event not found")
    item.state = "pending"
    await item.save()
    return {"status": "requeued"}
