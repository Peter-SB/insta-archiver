"""Service for downloading YouTube videos via yt-dlp.

Downloads audio (for transcription) or full video (when save_video=True)
and extracts metadata: title, channel, upload date, view/like counts,
and channel subscriber count.
"""

import os
import re
import logging
from dataclasses import dataclass

import yt_dlp

logger = logging.getLogger(__name__)


@dataclass
class VideoData:
    """Metadata extracted from a downloaded YouTube video."""

    video_id: str
    channel: str
    title: str
    upload_date: str
    view_count: int | None
    like_count: int | None
    channel_followers: int | None
    description: str
    media_path: str | None


def extract_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL.

    Supports watch?v=, youtu.be, /shorts/, and /embed/ URL formats.
    Raises ValueError if the format is not recognised.
    """
    patterns = [
        r"youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def download_video(url: str, folder: str, media_dir: str, save_video: bool = False) -> VideoData:
    """Download a YouTube video and return its metadata.

    When save_video is False (default), downloads audio only — much faster
    and sufficient for transcription. When save_video is True, downloads
    the best available video+audio format.

    Pipeline step 1 (YouTube): Downloads to {media_dir}/{folder}/{channel}/.
    """
    video_id = extract_video_id(url)

    ydl_opts_meta = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
        info = ydl.extract_info(url, download=False)

    channel = info.get("uploader") or info.get("channel") or "unknown_channel"
    channel = re.sub(r'[<>:"/\\|?*]', "_", channel)
    title = info.get("title", video_id)
    upload_date = info.get("upload_date", "")
    view_count = info.get("view_count")
    like_count = info.get("like_count")
    channel_followers = info.get("channel_follower_count")
    description = info.get("description", "")

    target_name = f"{channel}_{video_id}"
    output_dir = os.path.join(media_dir, folder, channel)
    os.makedirs(output_dir, exist_ok=True)

    if save_video:
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        outtmpl = os.path.join(output_dir, f"{target_name}.%(ext)s")
        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }
    else:
        outtmpl = os.path.join(output_dir, f"{target_name}.%(ext)s")
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        dl_info = ydl.extract_info(url, download=True)

    ext = dl_info.get("ext", "m4a") if not save_video else "mp4"
    media_path = os.path.join(output_dir, f"{target_name}.{ext}")
    if not os.path.exists(media_path):
        media_path = None

    logger.info("Downloaded YouTube video %s by %s", video_id, channel)

    return VideoData(
        video_id=video_id,
        channel=channel,
        title=title,
        upload_date=upload_date,
        view_count=view_count,
        like_count=like_count,
        channel_followers=channel_followers,
        description=description,
        media_path=media_path,
    )
