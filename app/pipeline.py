"""Pipeline orchestration for processing Instagram archive jobs.

Chains the three service steps in a clear, named sequence:
  1. download_post   — fetch video/image + metadata via Instaloader
  2. transcribe_audio — convert audio to text via Whisper (if video)
  3. write_note       — render and save Obsidian markdown

Each step is a pure function in its respective service module.
This module handles orchestration, status updates, and error handling.
"""

import logging
from datetime import datetime, timezone

from app import config
from app.database import update_job_status
from app.services import instaloader_service, whisper_service, markdown_service

logger = logging.getLogger(__name__)


def process_job(job: dict, whisper_model) -> None:
    """Run a single job through the full archive pipeline.

    Updates job status at each stage. On any failure, marks the job as
    'failed' with the error message so the UI can display it.
    """
    job_id = job["id"]
    url = job["url"]
    folder = job["folder"]

    try:
        update_job_status(job_id, "started")

        # Step 1: Download post
        logger.info("Job %d — downloading %s", job_id, url)
        post_data = instaloader_service.download_post(url, folder, config.DATA_DIR)
        update_job_status(job_id, "started", account_name=post_data.account_name)

        # Step 2: Transcribe audio (skip for image-only posts)
        transcript = ""
        if post_data.video_path:
            logger.info("Job %d — transcribing audio", job_id)
            transcript = whisper_service.transcribe_audio(whisper_model, post_data.video_path)
        else:
            logger.info("Job %d — no video, skipping transcription", job_id)

        # Step 3: Write markdown note
        logger.info("Job %d — writing markdown note", job_id)
        note_path = markdown_service.write_note(
            data_dir=config.DATA_DIR,
            folder=folder,
            account_name=post_data.account_name,
            shortcode=post_data.shortcode,
            url=url,
            description=post_data.description,
            transcript=transcript,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        )

        # Done
        update_job_status(job_id, "successful", note_path=note_path)
        logger.info("Job %d — completed: %s", job_id, note_path)

    except Exception as e:
        logger.error("Job %d — failed: %s", job_id, e, exc_info=True)
        update_job_status(job_id, "failed", error_message=str(e))
