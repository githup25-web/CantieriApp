from datetime import datetime, timezone

from app.scheduler.scheduler import scheduled_job
from app.models.event_queue import EventQueue


@scheduled_job(interval_seconds=10)
async def heartbeat() -> None:
    # Must include event_instance_id (required by EventQueue model)
    event_instance_id = f"heartbeat_{datetime.now(timezone.utc).timestamp()}".replace(".", "_")

    await EventQueue(
        event_instance_id=event_instance_id,
        event_name="system.heartbeat",
        payload={"timestamp": datetime.utcnow().isoformat()},
        state="pending",
        attempts=0,
        last_error=None,
        next_attempt_at=None,
        max_attempts=5,
    ).insert()
