from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.events_contract import normalize_event_context

Listener = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class Event:
    name: str
    context: dict[str, Any]


class EventDispatcher:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def register(self, event_name: str, listener: Listener) -> None:
        self._listeners[event_name].append(listener)

    async def dispatch(self, event_name: str, context: dict[str, Any]) -> None:
        # Normalize payload to the official event contract while staying compatible
        # with legacy producers/tests.
        normalized = normalize_event_context(event_name, context)

        # Lazy-load notification listeners so they work in scripts/tests that
        # don't run FastAPI startup events.
        if not self._listeners.get(event_name):
            # Keep backward-compatible lazy import behavior for legacy event prefixes.
            if event_name.startswith(
                (
                    "preventivo.",
                    "fattura.",
                    "task.",
                    "cantiere.",
                    "spesa.",
                    "presenza.",
                    "documento.",
                    "membership.",
                    "user.",
                )
            ):
                try:
                    # Import has side-effects: notification_service auto-registers listeners.
                    __import__("app.services.notification_service")
                except Exception:
                    # If notification module fails to import, keep dispatcher robust.
                    pass

        listeners = self._listeners.get(event_name, [])
        if not listeners:
            return
        for listener in listeners:
            await listener(normalized)


dispatcher = EventDispatcher()
