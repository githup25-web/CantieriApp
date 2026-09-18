import asyncio
import importlib
import logging
import pkgutil
from typing import Any, Awaitable, Callable, Dict, Optional

EVENT_HANDLERS: Dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {}

logger = logging.getLogger("app.worker.event_processor")


def register_event(event_type: str):
    def decorator(func: Callable[[dict], Awaitable[Any]]):
        EVENT_HANDLERS[event_type] = func
        return func

    return decorator


_loaded_handlers: bool = False


async def _load_handlers() -> None:
    """
    Import all modules in app/worker/handlers so their @register_event decorators run.
    """
    global _loaded_handlers
    if _loaded_handlers:
        return

    # Ensure async context doesn't block any caller.
    await asyncio.sleep(0)

    package_name = "app.worker.handlers"
    package = importlib.import_module(package_name)

    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        importlib.import_module(module_info.name)

    _loaded_handlers = True


async def process_event(event: dict[str, Any]) -> Any:
    await _load_handlers()

    event_id: Optional[Any] = event.get("event_id")
    event_type_val: Any = event.get("event_type")
    event_type: Optional[str] = event_type_val if isinstance(event_type_val, str) else None

    payload = event.get("payload")
    attempts_val: Any = event.get("attempts", 0)
    max_attempts_val: Any = event.get("max_attempts", 5)

    attempts: int = int(attempts_val) if isinstance(attempts_val, (int, str)) and str(attempts_val).isdigit() else 0
    max_attempts: int = int(max_attempts_val) if isinstance(max_attempts_val, (int, str)) and str(max_attempts_val).isdigit() else 5

    backoff_seconds = 2**attempts
    logger.info(
        "EventProcessor start event_id=%s event_type=%s attempts=%s/%s backoff_seconds=%s payload=%s",
        event_id,
        event_type,
        attempts,
        max_attempts,
        backoff_seconds,
        payload,
    )

    if event_type is None:
        raise ValueError("No handler registered for event_type=None")

    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        raise ValueError(f"No handler registered for event_type={event_type}")

    try:
        result = await handler(event)
        logger.info(
            "EventProcessor success event_id=%s event_type=%s result=%s",
            event_id,
            event_type,
            result,
        )

        # Emit "<event_type>.done" so workflows can chain on results.
        # (We intentionally do it after the handler succeeds.)
        from app.workflow.engine import emit_event

        await emit_event(
            event_type + ".done",
            {"result": result},
        )

        return result
    except Exception as e:
        logger.exception(
            "EventProcessor error event_id=%s event_type=%s attempts=%s/%s next_attempt_backoff_seconds=%s error=%s",
            event_id,
            event_type,
            attempts,
            max_attempts,
            backoff_seconds,
            e,
        )
        # Retry/backoff/DLQ are handled by the backend (/events/fail) which updates the DB.
        raise
