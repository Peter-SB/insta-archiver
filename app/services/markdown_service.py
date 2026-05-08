"""Service for writing Obsidian-compatible markdown notes.

Uses Jinja2 templates (app/templates/) so the output format can be changed
quickly without touching Python code. Supports both Instagram (note.md)
and YouTube (youtube_note.md) templates.
"""

import os
import logging

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
_env = Environment(
    loader=FileSystemLoader(_template_dir),
    keep_trailing_newline=True,
    autoescape=False,  # Markdown, not HTML — no escaping needed
)


def render_note(
    shortcode: str,
    account_name: str,
    url: str,
    description: str,
    transcript: str,
    folder: str,
    date: str,
) -> str:
    """Render a markdown note string from the note.md template."""
    template = _env.get_template("note.md")
    return template.render(
        shortcode=shortcode,
        account_name=account_name,
        url=url,
        description=description,
        transcript=transcript,
        folder=folder,
        date=date,
    )


def render_youtube_note(
    video_id: str,
    channel: str,
    title: str,
    upload_date: str,
    view_count,
    like_count,
    channel_followers,
    url: str,
    description: str,
    transcript: str,
    folder: str,
    date: str,
) -> str:
    """Render a markdown note string from the youtube_note.md template."""
    template = _env.get_template("youtube_note.md")
    return template.render(
        video_id=video_id,
        channel=channel,
        title=title,
        upload_date=upload_date,
        view_count=view_count,
        like_count=like_count,
        channel_followers=channel_followers,
        url=url,
        description=description,
        transcript=transcript,
        folder=folder,
        date=date,
    )


def write_note(
    markdown_dir: str,
    folder: str,
    account_name: str,
    shortcode: str,
    url: str,
    description: str,
    transcript: str,
    date: str,
) -> str:
    """Render and write a markdown note file.

    Pipeline step 3 (Instagram): Returns the path relative to markdown_dir for storage in DB.
    File is written to {markdown_dir}/{folder}/{account}_{shortcode}.md
    """
    content = render_note(
        shortcode=shortcode,
        account_name=account_name,
        url=url,
        description=description,
        transcript=transcript,
        folder=folder,
        date=date,
    )

    target_name = f"{account_name}_{shortcode}"
    account_dir = os.path.join(markdown_dir, folder, account_name)
    os.makedirs(account_dir, exist_ok=True)

    file_name = _unique_filename(account_dir, target_name)
    full_path = os.path.join(account_dir, file_name)
    relative_path = os.path.join(folder, account_name, file_name)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Wrote note: %s", relative_path)
    return relative_path


def write_youtube_note(
    markdown_dir: str,
    folder: str,
    channel: str,
    video_id: str,
    title: str,
    upload_date: str,
    view_count,
    like_count,
    channel_followers,
    url: str,
    description: str,
    transcript: str,
    date: str,
) -> str:
    """Render and write a YouTube markdown note file.

    Pipeline step 3 (YouTube): Returns the path relative to markdown_dir for storage in DB.
    File is written to {markdown_dir}/{folder}/{channel}/{channel}_{video_id}.md
    """
    content = render_youtube_note(
        video_id=video_id,
        channel=channel,
        title=title,
        upload_date=upload_date,
        view_count=view_count,
        like_count=like_count,
        channel_followers=channel_followers,
        url=url,
        description=description,
        transcript=transcript,
        folder=folder,
        date=date,
    )

    target_name = f"{channel}_{video_id}"
    channel_dir = os.path.join(markdown_dir, folder, channel)
    os.makedirs(channel_dir, exist_ok=True)

    file_name = _unique_filename(channel_dir, target_name)
    full_path = os.path.join(channel_dir, file_name)
    relative_path = os.path.join(folder, channel, file_name)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Wrote YouTube note: %s", relative_path)
    return relative_path


def _unique_filename(directory: str, base_name: str) -> str:
    """Return a deduplicated filename so existing notes are never overwritten."""
    file_name = f"{base_name}.md"
    if os.path.exists(os.path.join(directory, file_name)):
        count = 2
        while os.path.exists(os.path.join(directory, f"{base_name} ({count}).md")):
            count += 1
        file_name = f"{base_name} ({count}).md"
    return file_name
