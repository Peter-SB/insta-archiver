"""Background worker that processes archive jobs on-demand.

Design decision — idle resource usage:
  The Whisper model is large and should NOT sit in memory when idle.
  The worker sleeps until signalled, then:
    1. Loads the Whisper model
    2. Processes ALL waiting jobs sequentially
    3. Unloads the model (del + gc.collect)
    4. Returns to sleep

  This means a small delay (~2-5s) to load the model per batch, but zero
  idle CPU/RAM cost. For a personal archiving tool this the tradeoff.

Thread safety:
  Uses threading.Event for signalling. If multiple jobs are submitted while
  the worker is busy, the Event stays set and the worker picks them up in the
  same batch or immediately starts a new batch after finishing.
"""

import gc
import logging
import threading

from app import config
from app.database import get_next_waiting_job
from app.pipeline import process_job
from app.services import whisper_service

logger = logging.getLogger(__name__)

_wake_event = threading.Event()


def signal_worker() -> None:
    """Signal the worker to wake up and process any waiting jobs."""
    _wake_event.set()


def _worker_loop() -> None:
    """Main worker loop. Runs in a daemon thread, sleeps between batches."""
    logger.info("Worker thread started — waiting for jobs")

    while True:
        _wake_event.wait()
        _wake_event.clear()

        try:
            logger.info("Worker woken — loading Whisper model (%s)", config.WHISPER_MODEL)
            model = whisper_service.load_model(config.WHISPER_MODEL)

            try:
                while True:
                    job = get_next_waiting_job()
                    if job is None:
                        break
                    logger.info("Processing job %d: %s", job["id"], job["url"])
                    process_job(job, model)
            finally:
                del model
                gc.collect()
                logger.info("All jobs processed — Whisper model unloaded")

        except Exception:
            logger.exception("Worker cycle failed unexpectedly — will retry on next signal")


def start_worker() -> threading.Thread:
    """Start the background worker as a daemon thread.

    Called once at application startup via the FastAPI lifespan.
    """
    thread = threading.Thread(target=_worker_loop, daemon=True, name="job-worker")
    thread.start()
    return thread
