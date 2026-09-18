from worker.logger import logger
from worker.bootstrap import bootstrap
from worker.main import worker_loop
from worker.config import WORKER_NAME


def main():
    logger.info("Bootstrapping worker...")
    info = bootstrap()
    logger.info(f"Bootstrap completed: {info}")
    logger.info("Starting worker loop...")
    worker_loop(WORKER_NAME)


if __name__ == "__main__":
    main()
