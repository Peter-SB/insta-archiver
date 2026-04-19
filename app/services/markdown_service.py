"""Service for writing Obsidian-compatible markdown notes.

Uses a Jinja2 template (app/templates/note.md) so the output format
can be changed quickly without touching Python code.
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


def write_note(
    data_dir: str,
    folder: str,
    account_name: str,
    shortcode: str,
    url: str,
    description: str,
    transcript: str,
    date: str,
) -> str:
    """Render and write a markdown note file.

    Pipeline step 3: Returns the path relative to data_dir for storage in DB.
    File is written to {data_dir}/{folder}/{account}_{shortcode}/{account}_{shortcode}.md
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
    relative_path = os.path.join(folder, target_name, f"{target_name}.md")
    full_path = os.path.join(data_dir, relative_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Wrote note: %s", relative_path)
    return relative_path
