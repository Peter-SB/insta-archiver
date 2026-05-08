"""Pipeline orchestration for processing archive jobs.

Chains the three service steps in a clear, named sequence:
  1. download_post / download_video  — fetch media + metadata
  2. transcribe_audio                — convert audio to text via Whisper (if video/audio present)
  3. write_note / write_youtube_note — render and save Obsidian markdown

Status progression:
  waiting → downloading → transcribing → successful
                                        → failed (at any step)

Each step is a pure function in its respective service module.
This module handles orchestration, status updates, and error handling.
"""

import logging
import os
from datetime import datetime, timezone

from app import config
from app.database import update_job_status
from app.services import instaloader_service, whisper_service, markdown_service
from app.services import ytdlp_service

logger = logging.getLogger(__name__)


def _delete_video(video_path: str) -> None:
    """Delete a video file. Logs a warning if deletion fails but does not raise."""
    try:
        os.remove(video_path)
        os.rmdir(os.path.dirname(video_path))
        logger.info("Deleted video file: %s", video_path)
    except OSError as e:
        logger.warning("Could not delete video file %s: %s", video_path, e)


def _process_instagram_job(job: dict, whisper_model) -> None:
    """Run an Instagram job through the archive pipeline."""
    job_id = job["id"]
    url = job["url"]
    folder = job["folder"]
    save_video = bool(job.get("save_video", False))

    logger.info("Job %d — downloading %s", job_id, url)
    update_job_status(job_id, "downloading")
    post_data = instaloader_service.download_post(url, folder, config.MEDIA_DIR)
    update_job_status(job_id, "downloading", account_name=post_data.account_name)

    transcript = ""
    if post_data.video_path:
        logger.info("Job %d — transcribing audio", job_id)
        update_job_status(job_id, "transcribing", account_name=post_data.account_name)
        transcript = whisper_service.transcribe_audio(whisper_model, post_data.video_path)

        if not save_video:
            _delete_video(post_data.video_path)
    else:
        logger.info("Job %d — no video, skipping transcription", job_id)

    logger.info("Job %d — writing markdown note", job_id)
    note_path = markdown_service.write_note(
        markdown_dir=config.MARKDOWN_DIR,
        folder=folder,
        account_name=post_data.account_name,
        shortcode=post_data.shortcode,
        url=url,
        description=post_data.description,
        transcript=transcript,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )

    update_job_status(job_id, "successful", note_path=note_path)
    logger.info("Job %d — completed: %s", job_id, note_path)


def _process_youtube_job(job: dict, whisper_model) -> None:
    """Run a YouTube job through the archive pipeline."""
    job_id = job["id"]
    url = job["url"]
    folder = job["folder"]
    save_video = bool(job.get("save_video", False))

    logger.info("Job %d — downloading YouTube video %s", job_id, url)
    update_job_status(job_id, "downloading")
    video_data = ytdlp_service.download_video(url, folder, config.MEDIA_DIR, save_video=save_video)
    update_job_status(job_id, "downloading", account_name=video_data.channel)

    transcript = ""
    if video_data.media_path:
        logger.info("Job %d — transcribing audio", job_id)
        update_job_status(job_id, "transcribing", account_name=video_data.channel)
        transcript = whisper_service.transcribe_audio(whisper_model, video_data.media_path)

        if not save_video:
            _delete_video(video_data.media_path)
    else:
        logger.info("Job %d — no media file found, skipping transcription", job_id)

    logger.info("Job %d — writing markdown note", job_id)
    note_path = markdown_service.write_youtube_note(
        markdown_dir=config.MARKDOWN_DIR,
        folder=folder,
        channel=video_data.channel,
        video_id=video_data.video_id,
        title=video_data.title,
        upload_date=video_data.upload_date,
        view_count=video_data.view_count,
        like_count=video_data.like_count,
        channel_followers=video_data.channel_followers,
        url=url,
        description=video_data.description,
        transcript=transcript,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )

    update_job_status(job_id, "successful", note_path=note_path)
    logger.info("Job %d — completed: %s", job_id, note_path)


def process_job(job: dict, whisper_model) -> None:
    """Run a single job through the full archive pipeline.

    Updates job status at each stage. On any failure, marks the job as
    'failed' with the error message so the UI can display it.
    """
    job_id = job["id"]
    platform = job.get("platform", "instagram")

    try:
        if platform == "youtube":
            _process_youtube_job(job, whisper_model)
        else:
            _process_instagram_job(job, whisper_model)

    except Exception as e:
        logger.error("Job %d — failed: %s", job_id, e, exc_info=True)
        update_job_status(job_id, "failed", error_message=str(e))
