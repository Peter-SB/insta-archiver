"""FastAPI application — routes, lifespan, and HTMX SSR rendering.

Endpoints:
  GET  /         — Main page (form + job list)
  POST /jobs     — Submit a new archive job (with dedup warning)
  GET  /jobs     — Job list partial (for HTMX polling)
  GET  /folders  — Available output folders as JSON
  GET  /health   — Health check
"""

import os
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.database import init_db, create_job, get_all_jobs, job_exists_for_url
from app.services.instaloader_service import extract_shortcode
from app.services.ytdlp_service import extract_video_id
from app.worker import start_worker, signal_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB, create data subdirectories, start worker."""
    init_db()
    for directory in (config.DB_DIR, config.MEDIA_DIR,
                      os.path.join(config.MARKDOWN_DIR, config.DEFAULT_FOLDER),
                      os.path.join(config.MARKDOWN_DIR, config.YOUTUBE_DEFAULT_FOLDER)):
        os.makedirs(directory, exist_ok=True)
    start_worker()
    logger.info("Application started")
    yield


app = FastAPI(title="Insta & YouTube Archiver", lifespan=lifespan)


def _detect_platform(url: str) -> str:
    """Return 'youtube' for YouTube URLs, 'instagram' otherwise."""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    if host in ("youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"):
        return "youtube"
    return "instagram"


def _extract_id(url: str, platform: str) -> str:
    """Extract the content ID (shortcode or video ID) from a URL."""
    if platform == "youtube":
        return extract_video_id(url)
    return extract_shortcode(url)


def _list_folders() -> list[str]:
    """Scan MARKDOWN_DIR for subdirectories. Always includes the default folders.

    Scans MARKDOWN_DIR (not DATA_DIR) so the folder list reflects only note
    output locations. This lets MARKDOWN_DIR be mounted as an Obsidian vault
    while MEDIA_DIR is kept separate.
    """
    folders: set[str] = set()
    if os.path.isdir(config.MARKDOWN_DIR):
        for name in os.listdir(config.MARKDOWN_DIR):
            path = os.path.join(config.MARKDOWN_DIR, name)
            if os.path.isdir(path) and not name.startswith("."):
                folders.add(name)
    folders.add(config.DEFAULT_FOLDER)
    folders.add(config.YOUTUBE_DEFAULT_FOLDER)
    return sorted(folders)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page with submission form and job list."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "jobs": get_all_jobs(),
            "folders": _list_folders(),
            "default_folder": config.DEFAULT_FOLDER,
            "youtube_default_folder": config.YOUTUBE_DEFAULT_FOLDER,
        },
    )


@app.post("/jobs", response_class=HTMLResponse)
async def add_job(
    request: Request,
    url: str = Form(...),
    folder: str = Form(""),
    save_video: bool = Form(False),
    force: bool = Form(False),
):
    """Submit a new archive job.

    If the URL was already submitted, returns an HTMX warning partial with
    an 'Add Anyway' option — unless force=True.
    """
    platform = _detect_platform(url)

    if not folder:
        folder = config.YOUTUBE_DEFAULT_FOLDER if platform == "youtube" else config.DEFAULT_FOLDER

    try:
        content_id = _extract_id(url, platform)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "partials/job_form_result.html",
            {"error": str(e)},
        )

    if not force and job_exists_for_url(url):
        return templates.TemplateResponse(
            request,
            "partials/job_form_result.html",
            {"warning": True, "url": url, "folder": folder, "save_video": save_video},
        )

    create_job(url=url, shortcode=content_id, folder=folder, save_video=save_video, platform=platform)
    signal_worker()

    response = templates.TemplateResponse(
        request,
        "partials/job_form_result.html",
        {"success": True},
    )
    response.headers["HX-Trigger"] = "refreshJobs"
    return response


@app.get("/jobs", response_class=HTMLResponse)
async def list_jobs(request: Request):
    """Return the job list table partial for HTMX polling."""
    return templates.TemplateResponse(
        request,
        "partials/job_list.html",
        {"jobs": get_all_jobs()},
    )


@app.get("/folders")
async def list_folders():
    """Return available output folders as JSON (for dynamic dropdowns)."""
    return _list_folders()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
