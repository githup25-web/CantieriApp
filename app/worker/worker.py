from __future__ import annotations

import asyncio

from dispatcher.client import ack as dispatcher_ack
from dispatcher.client import fail as dispatcher_fail
from dispatcher.client import fetch_event as dispatcher_fetch_event
from worker.config import WORKER_SLEEP_SECONDS, WORKER_NAME

from app.worker.event_processor import process_event


async def process_event_item(event: dict) -> None:
    return await process_event(event)


async def run_worker(*, poll_interval_seconds: float = WORKER_SLEEP_SECONDS) -> None:
    while True:
        event = dispatcher_fetch_event(WORKER_NAME)
        if event is None:
            await asyncio.sleep(poll_interval_seconds)
            continue

        try:
            await process_event_item(event=event)
            dispatcher_ack(str(event["event_id"]))
        except Exception as e:
            dispatcher_fail(str(event["event_id"]), str(e))

        # Avoid tight loop if backend keeps returning the same item.
        await asyncio.sleep(poll_interval_seconds)


def main() -> None:
    asyncio.run(run_worker())
