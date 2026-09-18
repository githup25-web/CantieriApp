from worker.config import WORKER_NAME
from worker.utils import utcnow


def ping():
    return "pong"


def status():
    return {
        "worker": WORKER_NAME,
        "status": "ok",
        "timestamp": utcnow(),
    }
