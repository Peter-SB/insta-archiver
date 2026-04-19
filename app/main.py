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

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.database import init_db, create_job, get_all_jobs, job_exists_for_url
from app.services.instaloader_service import extract_shortcode
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
    """Startup: initialise DB, ensure default folder exists, start worker."""
    init_db()
    os.makedirs(os.path.join(config.DATA_DIR, config.DEFAULT_FOLDER), exist_ok=True)
    start_worker()
    logger.info("Application started")
    yield


app = FastAPI(title="Instagram Archiver", lifespan=lifespan)


def _list_folders() -> list[str]:
    """Scan DATA_DIR for subdirectories. Always includes the default folder."""
    folders: set[str] = set()
    if os.path.isdir(config.DATA_DIR):
        for name in os.listdir(config.DATA_DIR):
            path = os.path.join(config.DATA_DIR, name)
            if os.path.isdir(path) and not name.startswith("."):
                folders.add(name)
    folders.add(config.DEFAULT_FOLDER)
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
        },
    )


@app.post("/jobs", response_class=HTMLResponse)
async def add_job(
    request: Request,
    url: str = Form(...),
    folder: str = Form(config.DEFAULT_FOLDER),
    force: bool = Form(False),
):
    """Submit a new archive job.

    If the URL was already submitted, returns an HTMX warning partial with
    an 'Add Anyway' option — unless force=True.
    """
    # Validate URL
    try:
        shortcode = extract_shortcode(url)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "partials/job_form_result.html",
            {"error": str(e)},
        )

    # Dedup check
    if not force and job_exists_for_url(url):
        return templates.TemplateResponse(
            request,
            "partials/job_form_result.html",
            {"warning": True, "url": url, "folder": folder},
        )

    # Create job and wake the worker
    create_job(url=url, shortcode=shortcode, folder=folder)
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
