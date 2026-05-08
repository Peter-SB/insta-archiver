# Instagram & YouTube Archiver

A single-container Docker service that downloads Instagram posts/reels and YouTube videos, transcribes audio with OpenAI Whisper, and saves everything as Obsidian-compatible markdown notes.

## Features

- **HTMX frontend** — Submit URLs, pick an output folder, and monitor job status in real time (4-second polling).
- **Instagram archive** — Downloads post via Instaloader → transcribes audio via faster-whisper → writes markdown.
- **YouTube archive** — Downloads audio (or full video) via yt-dlp → transcribes via faster-whisper → writes markdown with metadata (title, channel, upload date, view/like counts, subscriber count).
- **Obsidian markdown output** — YAML frontmatter with title, URL, account/channel, date, folder. Body has description + transcript. Templates at `app/templates/note.md` and `app/templates/youtube_note.md` for easy customisation.
- **Platform folders** — Instagram notes default to "Insta Archive"; YouTube notes default to "YouTube Archive".
- **Save media toggle** — Optionally keep the downloaded video/audio file after transcription.
- **Dedup with override** — Warns when a URL was already submitted; "Add Anyway" button allows re-archiving.
- **On-demand Whisper** — Model loads only when jobs are queued, unloads after the batch completes. Zero idle CPU/RAM cost.

## Quick Start

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000), paste an Instagram reel/post or YouTube video URL, pick a folder, and click **Archive**.

## Supported URL formats

| Platform  | Example URLs |
|-----------|-------------|
| Instagram | `https://www.instagram.com/reel/ABC123/` |
| Instagram | `https://www.instagram.com/p/ABC123/` |
| YouTube   | `https://www.youtube.com/watch?v=VIDEO_ID` |
| YouTube   | `https://youtu.be/VIDEO_ID` |
| YouTube   | `https://www.youtube.com/shorts/VIDEO_ID` |

## Configuration

| Env var         | Default  | Description                                        |
|-----------------|----------|----------------------------------------------------|
| `DATA_DIR`      | `/data`  | Mount point for output files and SQLite database    |
| `WHISPER_MODEL` | `base`   | faster-whisper model size (`tiny`, `base`, `small`) |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  FastAPI  (app/main.py)                             │
│  GET /          — HTMX page (form + job list)       │
│  POST /jobs     — Submit URL (platform detection)   │
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
│  Instagram:                                         │
│    1. download_post()     — Instaloader             │
│    2. transcribe_audio()  — faster-whisper          │
│    3. write_note()        — Jinja2 markdown         │
│  YouTube:                                           │
│    1. download_video()    — yt-dlp                  │
│    2. transcribe_audio()  — faster-whisper          │
│    3. write_youtube_note() — Jinja2 markdown        │
└─────────────────────────────────────────────────────┘
```

### Project Structure

```
app/
├── config.py                  # Env var configuration
├── database.py                # SQLite CRUD (thread-safe)
├── pipeline.py                # Pipeline orchestration (Instagram + YouTube)
├── worker.py                  # Background worker (on-demand Whisper)
├── main.py                    # FastAPI routes + lifespan
├── services/
│   ├── instaloader_service.py # Instagram download + metadata extraction
│   ├── ytdlp_service.py       # YouTube download + metadata extraction
│   ├── whisper_service.py     # Audio transcription (shared by both pipelines)
│   └── markdown_service.py    # Template rendering + file writing
└── templates/
    ├── index.html             # HTMX frontend
    ├── note.md                # Obsidian markdown template (Instagram)
    ├── youtube_note.md        # Obsidian markdown template (YouTube)
    └── partials/
        ├── job_list.html      # Job table (HTMX partial)
        └── job_form_result.html # Success/warning/error messages
```

## YouTube Metadata

YouTube notes include the following metadata in YAML frontmatter and the note body:

| Field               | Source                                |
|---------------------|---------------------------------------|
| `title`             | Video title                           |
| `channel`           | Uploader / channel name               |
| `upload_date`       | Original upload date (YYYYMMDD)       |
| `view_count`        | Total view count                      |
| `like_count`        | Like count                            |
| `channel_followers` | Subscriber count                      |
| `description`       | Video description                     |

Fields not available from yt-dlp are recorded as `~` (YAML null).

## Technical Details

- **SQLite** tracks jobs with status (`waiting` → `downloading` → `transcribing` → `successful`/`failed`) and a `platform` column (`instagram` or `youtube`). URL is not unique so the same post can be re-archived via "Add Anyway".
- **Background worker** picks up jobs from the SQLite queue sequentially, reducing concurrent resource load. Whisper model is loaded per-batch and freed after all jobs complete.
- **Thread-local DB connections** ensure safe concurrent access from the API thread and worker thread.
- **Platform detection** identifies Instagram vs YouTube from the submitted URL, routing to the appropriate download service.
- **YouTube downloads** fetch audio-only by default (much faster, sufficient for transcription). When "Save media file" is checked, the full video is downloaded instead.
- **Dynamic folder list** scans `MARKDOWN_DIR` subdirectories. "Insta Archive" and "YouTube Archive" are always available as defaults.
- **File naming** uses `{account}_{shortcode}` for Instagram and `{channel}_{video_id}` for YouTube.

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
| Jinja2 markdown templates | Output format can be changed by editing templates without touching Python |
| Sequential worker | Matches the "reduce concurrent resource load" goal; no need for async job queue |
| Audio-only YouTube download | Transcription only needs audio; skipping video reduces download time and storage |
| Shared whisper_service | Both Instagram and YouTube pipelines reuse the same transcription code |
