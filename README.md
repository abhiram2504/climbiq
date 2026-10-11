# ClimbIQ

ClimbIQ is a local-first indoor bouldering analysis application. Phase 2 accepts climbing videos, runs MediaPipe Pose Landmarker locally, persists timestamped body landmarks, and produces an annotated review video alongside the original attempt.

> **Phase boundary:** Phase 2 measures and visualizes pose. Joint-angle metrics, movement segmentation, and evidence-based technique observations remain Phase 3 work; the app does not invent technique verdicts from raw landmarks.

## Architecture

```text
Browser (React + TypeScript + Vite + Tailwind)
              │ /api
              ▼
FastAPI ── SQLAlchemy/Alembic ── PostgreSQL
   │                  │
   │                  └── processing jobs + 33-landmark samples
   └── local pose executor ── MediaPipe + OpenCV + FFmpeg
                            └── original and annotated video files
```

Videos are stored outside PostgreSQL. Database rows keep metadata and storage keys, while normalized landmark samples are stored in PostgreSQL. Processing uses a single-worker local executor for the MVP and preserves a queue boundary that can be replaced by Celery/Redis in Phase 4.

## Repository layout

```text
climbiq/
├── backend/           FastAPI app, SQLAlchemy models, Alembic, pytest
├── frontend/          React/Vite/Tailwind dashboard
├── infrastructure/    Monitoring placeholders for Phase 4
├── data/              Local media (ignored by Git)
├── scripts/           Developer checks
├── .github/workflows/ CI checks
├── docker-compose.yml
└── .env.example
```

## Prerequisites

- Docker Desktop with Docker Compose (recommended), or
- Python 3.12, Node.js 22.12+, npm, FFmpeg, and a PostgreSQL 16 instance

No NVIDIA GPU or cloud account is required. Pose inference runs on the backend CPU.

## Run with Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Dashboard: <http://localhost:5173>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/health>

The backend applies Alembic migrations on startup. Uploaded files are written to `data/videos/`; PostgreSQL data lives in the named `postgres_data` Docker volume.

Stop the stack with `docker compose down`. Add `-v` only when you intentionally want to delete the local PostgreSQL volume.

## Run services directly

Start only PostgreSQL:

```bash
cp .env.example .env
docker compose up -d postgres
```

Backend (Python must be 3.12):

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cd ..
python backend/.venv/bin/python scripts/download_pose_model.py
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Tests and checks

```bash
cd backend
source .venv/bin/activate
pytest
ruff check .

cd ../frontend
npm run test
npm run typecheck
npm run build
```

Backend tests use a temporary SQLite database and temporary media directory, so they do not modify development data or require PostgreSQL. The computer-vision test uses a generated video, a deterministic fake detector, and the real FFmpeg H.264 output path; no private climbing footage is committed.

## API

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/health` | API and database readiness |
| `POST` | `/api/videos/upload` | Validate, store, and queue an MP4/MOV video |
| `GET` | `/api/videos` | List attempts, newest first |
| `GET` | `/api/videos/{id}` | Read attempt metadata |
| `GET` | `/api/videos/{id}/status` | Read processing status and progress |
| `POST` | `/api/videos/{id}/process` | Retry or rerun pose processing |
| `GET` | `/api/videos/{id}/stream` | Stream the original video |
| `GET` | `/api/videos/{id}/analysis` | Phase-aware analysis status; metrics remain Phase 3 |
| `GET` | `/api/videos/{id}/annotated` | Stream the H.264 pose-overlay video when complete |
| `GET` | `/api/sessions` | List climbing sessions and attempt counts |

Upload rules are configured by `MAX_UPLOAD_SIZE_MB` and `MAX_VIDEO_DURATION_SECONDS`. Only `.mp4` and `.mov` files with an ISO base media `ftyp` signature are accepted. Files are written through a temporary `.part` file, size-checked while streaming, and atomically renamed after validation. Client filenames are never used as storage paths.

Pose inference defaults to 8 FPS, one person, and the pinned MediaPipe Full float16 v1 bundle. Each sampled frame records all 33 landmark names; absent or low-presence points are stored explicitly with `detected=false` and null coordinates. The overlay keeps the source frame rate and available audio, then FFmpeg produces H.264/yuv420p output suitable for Safari and Chrome.

## Configuration

Copy `.env.example` to `.env` and adjust as needed. Do not commit `.env` or real climbing videos. `CORS_ORIGINS` accepts a comma-separated list. In production, use a unique database password, serve the API behind TLS, and replace local storage with managed object storage.

## Phase 2 assumptions and limitations

- MOV is a container, not a codec. The original may not play in every browser, but completed annotated output is transcoded to H.264.
- A lightweight file signature check prevents renamed arbitrary files, but is not a malware scanner.
- There is no authentication in the single-user local MVP.
- One climber is tracked per video. Occluded and off-screen landmarks are retained as missing data rather than guessed.
- The local executor is intentionally single-process. Keep the backend running until a job finishes; interrupted jobs are re-queued at the next startup.
- Monitoring directories are reserved for Phase 4. Redis and Celery are deliberately deferred while the processing interface remains queue-compatible.

## Next phase

Phase 3 will derive joint angles, body alignment, movement intervals, and transparent heuristic observations from the stored landmark track. Those results should include confidence and evidence timestamps and remain descriptive rather than absolute judgments of correctness.
