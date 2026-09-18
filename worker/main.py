import logging
import os
import signal
import sys
import time
from multiprocessing import Process
from typing import Dict

# Ensure the project root is on PYTHONPATH so "import app.*" works when running:
#   python worker/main.py
# This fixes: ModuleNotFoundError: No module named 'app'
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from beanie import init_beanie
from beanie.odm.enums import SortDirection

from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.events import dispatcher
from app.core.events_contract import normalize_event_context
from app.models.cantiere import Cantiere
from app.models.cantiere_document import CantiereDocument
from app.models.event_queue import EventQueue
from app.models.event_record import EventRecord
from app.models.expense import Expense
from app.models.fattura import Fattura
from app.models.invite import Invite
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.presence import Presence
from app.models.progress_photo import ProgressPhoto
from app.models.preventivo import Preventivo
from app.models.task import Task
from app.models.user import User
from app.services.notification_service import register_notification_listeners


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("worker-master")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(processName)s[%(process)d] | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def worker_loop(worker_id: int, sleep_s: float = 0.5) -> None:
    """
    Worker loop:
    - connessione a MongoDB con motor/beanie
    - ciclo infinito while True
    - chiama fetch_pending_event()
    - se evento trovato -> process_event()
    - aggiorna stato evento
    - sleep(0.5)
    """
    logger = logging.getLogger("worker")
    logger.setLevel(logging.INFO)

    # ensure handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(processName)s[%(process)d] | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    pid = os.getpid()
    logger.info(f"Worker loop started (worker_id={worker_id}, pid={pid})")

    async def fetch_pending_event() -> EventQueue | None:
        return await (
            EventQueue.find(EventQueue.state == "pending")
            .sort([("occurred_at", SortDirection.DESCENDING), ("id", SortDirection.ASCENDING)])
            .first_or_none()
        )

    async def process_event(item: EventQueue) -> None:
        # Best-effort state transition: pending -> processing
        item.state = "processing"
        item.attempts = int(item.attempts or 0) + 1
        item.last_error = None
        await item.save()

        payload = item.payload or {}
        event_name = item.event_name

        try:
            normalized = normalize_event_context(event_name, payload)
            await dispatcher.dispatch(event_name, normalized)

            item.state = "done"
            item.last_error = None
            await item.save()
        except Exception as e:
            item.state = "error"
            item.last_error = str(e)
            await item.save()
            raise

    async def _run() -> None:
        await connect_to_mongo()

        await init_beanie(
            # FastAPI uses settings.mongo_uri/mongo_db_name. For worker we rely on env vars too.
            connection_string=f"{os.getenv('MONGO_URI', '')}/{os.getenv('MONGO_DB_NAME', '')}",
            document_models=[
                User,
                Organization,
                Membership,
                Invite,
                Presence,
                Expense,
                ProgressPhoto,
                Task,
                Cantiere,
                CantiereDocument,
                Preventivo,
                Fattura,
                # notifications
                Notification,
                # event persistence/queue
                EventRecord,
                EventQueue,
            ],
        )

        # Ensure dispatcher listeners are registered in this process too (non-fatal if it fails).
        try:
            await register_notification_listeners()
        except Exception:
            logger.exception("Failed to register notification listeners; continuing")

        while True:
            try:
                item = await fetch_pending_event()
                if item is not None:
                    await process_event(item)
                time.sleep(sleep_s)
            except KeyboardInterrupt:
                return
            except Exception:
                # Let crash to enable master restart.
                logger.exception(f"Worker loop crashed (worker_id={worker_id})")
                raise

    import asyncio

    try:
        asyncio.run(_run())
    finally:
        try:
            asyncio.run(close_mongo_connection())
        except Exception:
            pass


def start_master(num_workers: int = 4, monitor_interval_s: float = 2.0) -> None:
    """
    Master che:
    - avvia N worker paralleli (multiprocessing.Process)
    - monitorizza i worker
    - se un worker crasha, lo riavvia
    - stampa log di avvio e monitoraggio
    """
    logger = _configure_logging()

    if num_workers < 1:
        raise ValueError("num_workers must be >= 1")

    logger.info(f"Master starting (pid={os.getpid()}) with num_workers={num_workers}")

    workers: Dict[int, Process] = {}
    stopping = False

    def _request_stop(signum: int, frame) -> None:
        nonlocal stopping
        stopping = True
        logger.warning(f"Master received signal {signum}; stopping workers...")

    # Graceful stop on common signals
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    def _spawn_worker(worker_id: int) -> Process:
        p = Process(
            target=worker_loop,
            name=f"worker-{worker_id}",
            args=(worker_id,),
            daemon=False,
        )
        p.start()
        logger.info(
            f"Spawned worker (worker_id={worker_id}, pid={p.pid}, alive={p.is_alive()})"
        )
        return p

    for worker_id in range(num_workers):
        workers[worker_id] = _spawn_worker(worker_id)

    try:
        while not stopping:
            time.sleep(monitor_interval_s)

            for worker_id, p in list(workers.items()):
                if not p.is_alive():
                    exitcode = p.exitcode
                    logger.error(
                        f"Worker crashed or stopped (worker_id={worker_id}, pid={p.pid}, exitcode={exitcode}). Restarting..."
                    )
                    workers[worker_id] = _spawn_worker(worker_id)

            alive_count = sum(1 for p in workers.values() if p.is_alive())
            logger.info(f"Master monitor tick: {alive_count}/{num_workers} workers alive")

    except KeyboardInterrupt:
        logger.warning("Master KeyboardInterrupt; stopping workers...")
    finally:
        for worker_id, p in workers.items():
            if p.is_alive():
                logger.info(f"Terminating worker (worker_id={worker_id}, pid={p.pid})")
                p.terminate()

        for worker_id, p in workers.items():
            logger.info(f"Joining worker (worker_id={worker_id}, pid={p.pid})")
            p.join(timeout=10)

        logger.info("Master shutdown complete.")


if __name__ == "__main__":
    workers_env = os.getenv("WORKER_NUM", "").strip()
    num_workers: int = 4
    if workers_env.isdigit():
        num_workers = int(workers_env)

    start_master(num_workers=num_workers)
