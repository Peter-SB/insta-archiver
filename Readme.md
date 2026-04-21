# Instagram Archiver

A single-container Docker service that downloads Instagram posts/reels, transcribes audio with OpenAI Whisper, and saves everything as Obsidian-compatible markdown notes.

## Features

- **HTMX frontend** — Submit URLs, pick an output folder, and monitor job status in real time (4-second polling).
- **Archive pipeline** — Downloads post via Instaloader → transcribes audio via faster-whisper → writes markdown.
- **Obsidian markdown output** — YAML frontmatter with title, URL, account, date, folder. Body has description + transcript. Template at `app/templates/note.md` for easy customisation.
- **Dedup with override** — Warns when a URL was already submitted; "Add Anyway" button allows re-archiving.
- **On-demand Whisper** — Model loads only when jobs are queued, unloads after the batch completes. Zero idle CPU/RAM cost.

## Quick Start

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000), paste an Instagram reel/post URL, pick a folder, and click **Archive**.

Archived notes appear in `./data/<folder>/<account>_<shortcode>/<account>_<shortcode>.md`.

## Configuration

| Env var         | Default  | Description                                       |
|-----------------|----------|---------------------------------------------------|
| `DATA_DIR`      | `/data`  | Mount point for output files and SQLite database   |
| `WHISPER_MODEL` | `base`   | faster-whisper model size (`tiny`, `base`, `small`) |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  FastAPI  (app/main.py)                             │
│  GET /          — HTMX page (form + job list)       │
│  POST /jobs     — Submit URL (dedup check)          │
│  GET  /jobs     — Job list partial (HTMX polling)   │
│  GET  /folders  — Dynamic folder list               │
│  GET  /health   — Health check                      │
└───────┬─────────────────────────────────────────────┘
        │  signal_worker()
        ▼
┌─────────────────────────────────────────────────────┐
│  Worker Thread  (app/worker.py)                     │
│  Sleeps until signalled → loads Whisper model →     │
│  processes ALL waiting jobs → unloads model → sleep │
└───────┬─────────────────────────────────────────────┘
        │  process_job()
        ▼
┌─────────────────────────────────────────────────────┐
│  Pipeline  (app/pipeline.py)                        │
│  1. download_post()    — Instaloader                │
│  2. transcribe_audio() — faster-whisper             │
│  3. write_note()       — Jinja2 markdown template   │
└─────────────────────────────────────────────────────┘
```

### Project Structure

```
app/
├── config.py                  # Env var configuration
├── database.py                # SQLite CRUD (thread-safe)
├── pipeline.py                # Pipeline orchestration
├── worker.py                  # Background worker (on-demand Whisper)
├── main.py                    # FastAPI routes + lifespan
├── services/
│   ├── instaloader_service.py # Download + metadata extraction
│   ├── whisper_service.py     # Audio transcription
│   └── markdown_service.py    # Template rendering + file writing
└── templates/
    ├── index.html             # HTMX frontend
    ├── note.md                # Obsidian markdown template
    └── partials/
        ├── job_list.html      # Job table (HTMX partial)
        └── job_form_result.html # Success/warning/error messages
```

## Technical Details

- **SQLite** tracks jobs with status (`waiting` → `started` → `successful`/`failed`). URL is not unique so the same post can be re-archived via "Add Anyway".
- **Background worker** picks up jobs from the SQLite queue sequentially, reducing concurrent resource load. Whisper model is loaded per-batch and freed after all jobs complete.
- **Thread-local DB connections** ensure safe concurrent access from the API thread and worker thread.
- **Dynamic folder list** scans `DATA_DIR` subdirectories. "Insta Archive" is always available as the default.
- **File naming** uses `{account}_{shortcode}` for human-readable output directories and filenames.

## Testing

See [Tests_Readme.md](Tests_Readme.md) for the test strategy and how to run tests.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single container | Simpler deployment for a personal tool; no inter-service networking needed |
| On-demand Whisper loading | Avoids persistent memory usage; ~3s load time per batch is acceptable |
| SQLite over Postgres | Zero-config, file-based, perfect for single-user sequential processing |
| HTMX over SPA framework | Server-rendered partials keep the frontend simple with no build step |
| Jinja2 markdown template | Output format can be changed by editing `note.md` without touching Python |
| Sequential worker | Matches the "reduce concurrent resource load" goal; no need for async job queue |
