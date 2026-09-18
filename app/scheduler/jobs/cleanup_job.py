import logging
from datetime import datetime, timedelta, timezone

from app.scheduler.scheduler import scheduled_job
from app.models.dead_letter import DeadLetter

logger = logging.getLogger("app.scheduler.cleanup_dlq")


@scheduled_job(interval_seconds=60)
async def cleanup_dlq() -> None:
    """
    Cleanup DLQ (DeadLetter) bounded + safe.
    This prevents periodic crashes due to heavy deletes on large collections.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        # Batch delete: fetch a limited set of old ids, then delete them by id.
        # This keeps memory usage bounded and reduces long-running operations.
        batch_size = 1000

        old_items = (
            await DeadLetter.find({"failed_at": {"$lt": cutoff}})
            .sort("-failed_at")
            .limit(batch_size)
            .to_list()
        )

        if not old_items:
            return

        ids = [it.id for it in old_items]

        # Beanie/Pylance compatibility: use raw Mongo query for $in on _id.
        await DeadLetter.find({"_id": {"$in": ids}}).delete()

    except Exception:
        # Scheduler must never crash.
        logger.exception("cleanup_dlq failed")
