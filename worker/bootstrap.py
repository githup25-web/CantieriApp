from worker.config import WORKER_NAME
from worker.version import get_version
from worker.logger import logger
from worker.context import CONTEXT
from worker.metrics import METRICS


def bootstrap():
    CONTEXT["worker"] = WORKER_NAME
    CONTEXT["version"] = get_version()
    METRICS["bootstrapped"] = 1
    logger.info(f"Worker {WORKER_NAME} bootstrapped (version {get_version()})")
    return {
        "worker": WORKER_NAME,
        "version": get_version(),
        "status": "bootstrapped"
    }
