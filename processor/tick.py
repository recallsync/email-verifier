"""Background tick loop — invokes process_chunk on interval."""

import logging
import os
import signal
import sys
import time

from config import CHUNK_TICK_INTERVAL
from migrations.run import run_migrations
from processor.chunk import process_chunk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [processor] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

_running = True


def _handle_shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received, stopping tick loop")
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    logger.info("Waiting for database...")
    for attempt in range(30):
        try:
            run_migrations()
            break
        except Exception as exc:
            logger.warning("Database not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(2)
    else:
        logger.error("Could not connect to database after 30 attempts")
        sys.exit(1)

    interval = int(os.environ.get("CHUNK_TICK_INTERVAL", CHUNK_TICK_INTERVAL))
    logger.info("Chunk processor started (interval=%ds)", interval)

    while _running:
        process_chunk()
        time.sleep(interval)

    logger.info("Chunk processor stopped")


if __name__ == "__main__":
    main()
