"""Service for downloading Instagram posts via Instaloader.

Downloads video/image and extracts metadata (caption, account name).
Uses {account_name}_{shortcode} naming for readability.
"""

import os
import re
import logging
from dataclasses import dataclass

from instaloader import Instaloader, Post

logger = logging.getLogger(__name__)


@dataclass
class PostData:
    """Metadata extracted from a downloaded Instagram post."""

    shortcode: str
    account_name: str
    video_path: str | None
    description: str


def extract_shortcode(url: str) -> str:
    """Extract the shortcode from an Instagram URL.

    Supports /reel/, /reels/, and /p/ URL formats.
    Raises ValueError if the format is not recognised.
    """
    match = re.search(r"(?:reel|reels|p)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Could not extract shortcode from URL: {url}")
    return match.group(1)


def download_post(url: str, folder: str, media_dir: str) -> PostData:
    """Download an Instagram post and return its metadata.

    Pipeline step 1: Downloads to {media_dir}/{folder}/{account}/.
    Creates a fresh Instaloader instance per call to avoid shared state.
    """
    shortcode = extract_shortcode(url)

    # Create loader — query post metadata first, then configure download paths
    loader = Instaloader(
        download_comments=False,
        save_metadata=False,
        download_video_thumbnails=False,
        download_geotags=False,
        post_metadata_txt_pattern="",
    )

    post = Post.from_shortcode(loader.context, shortcode)
    account_name = post.owner_username
    target_name = f"{account_name}_{shortcode}"

    # Configure download directory after we know the account name
    loader.dirname_pattern = os.path.join(media_dir, folder, account_name)
    loader.filename_pattern = target_name
    loader.download_post(post, target=target_name)

    logger.info("Downloaded post %s by @%s", shortcode, account_name)

    video_path = None
    if post.is_video:
        video_path = os.path.join(media_dir, folder, account_name, f"{target_name}.mp4")

    return PostData(
        shortcode=shortcode,
        account_name=account_name,
        video_path=video_path,
        description=post.caption or "",
    )
