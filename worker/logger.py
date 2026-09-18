import logging

from worker.config import WORKER_NAME, LOG_LEVEL

logger = logging.getLogger(WORKER_NAME)
logger.setLevel(LOG_LEVEL)

handler = logging.StreamHandler()
handler.setLevel(LOG_LEVEL)

formatter = logging.Formatter(
    "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)

logger.addHandler(handler)
