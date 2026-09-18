import asyncio
import importlib
import pkgutil
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Tuple

from app.models.event_queue import EventQueue  # noqa: F401  (used by jobs)


SCHEDULED_JOBS: List[Tuple[int, Callable[[], Awaitable[Any]]]] = []

# Track last execution time per function (or job function object).
_last_run_by_func: Dict[Callable[..., Any], datetime] = {}


def scheduled_job(interval_seconds: int):
    def decorator(func: Callable[[], Awaitable[Any]]):
        SCHEDULED_JOBS.append((interval_seconds, func))
        return func

    return decorator


async def run_scheduled_jobs() -> None:
    now = datetime.now(timezone.utc)

    for interval_seconds, func in list(SCHEDULED_JOBS):
        last_run = _last_run_by_func.get(func)
        if last_run is None:
            should_run = True
        else:
            should_run = (now - last_run).total_seconds() >= interval_seconds

        if not should_run:
            continue

        try:
            await func()
            _last_run_by_func[func] = now
        except Exception:
            # Scheduler must not crash backend; just log and continue.
            import logging

            logging.getLogger("app.scheduler").exception(
                "Scheduled job failed job=%s interval_seconds=%s",
                getattr(func, "__name__", str(func)),
                interval_seconds,
            )


async def scheduler_loop() -> None:
    while True:
        await run_scheduled_jobs()
        await asyncio.sleep(1)


def _load_jobs() -> None:
    """
    Auto-load all modules in app.scheduler.jobs so their @scheduled_job
    decorators register jobs into SCHEDULED_JOBS.
    """
    pkg = "app.scheduler.jobs"
    # Convert dots to path separators for pkgutil search.
    search_path = pkg.replace(".", "/")

    for _, module_name, _ in pkgutil.iter_modules([search_path]):
        importlib.import_module(f"{pkg}.{module_name}")


# Ensure jobs are registered as soon as the scheduler module is imported.
_load_jobs()
