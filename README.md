# ClimbIQ

ClimbIQ is a local-first indoor bouldering analysis application. Phase 1 provides the production-shaped foundation: safe video uploads, PostgreSQL persistence, attempt history, status reporting, video playback, a responsive React dashboard, database migrations, and automated tests.

> **Phase boundary:** pose estimation, annotated output, movement metrics, and technique observations are intentionally not implemented yet. The API models and response contracts are ready for those Phase 2 and 3 features, and the UI labels them as pending rather than showing invented results.

## Architecture

```text
Browser (React + TypeScript + Vite + Tailwind)
              │ /api
              ▼
FastAPI ── SQLAlchemy/Alembic ── PostgreSQL
   │
   └── UUID-named video files in data/videos/
```

Videos are stored outside PostgreSQL. Database rows keep metadata and a storage key, so local storage can later be replaced by object storage without changing the API contract. The analysis-oriented tables are included in the initial migration but remain empty in Phase 1.

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
- Python 3.12, Node.js 22.12+, npm, and a PostgreSQL 16 instance

No NVIDIA GPU or cloud account is required for Phase 1.

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

Backend tests use a temporary SQLite database and temporary media directory, so they do not modify development data or require PostgreSQL. PostgreSQL behavior is covered by the same SQLAlchemy models and is exercised when the Docker stack starts and runs its migration.

## API

| Method | Path | Phase 1 behavior |
| --- | --- | --- |
| `GET` | `/api/health` | API and database readiness |
| `POST` | `/api/videos/upload` | Validate and store MP4/MOV video |
| `GET` | `/api/videos` | List attempts, newest first |
| `GET` | `/api/videos/{id}` | Read attempt metadata |
| `GET` | `/api/videos/{id}/status` | Read processing status |
| `GET` | `/api/videos/{id}/stream` | Stream the original video |
| `GET` | `/api/videos/{id}/analysis` | Empty, explicit `not_started` analysis payload |
| `GET` | `/api/videos/{id}/annotated` | `404` until Phase 2 output exists |
| `GET` | `/api/sessions` | List climbing sessions and attempt counts |

Upload rules are configured by `MAX_UPLOAD_SIZE_MB`. Only `.mp4` and `.mov` files with an ISO base media `ftyp` signature are accepted. Files are written through a temporary `.part` file, size-checked while streaming, and atomically renamed after validation. Client filenames are never used as storage paths.

## Configuration

Copy `.env.example` to `.env` and adjust as needed. Do not commit `.env` or real climbing videos. `CORS_ORIGINS` accepts a comma-separated list. In production, use a unique database password, serve the API behind TLS, and replace local storage with managed object storage.

## Phase 1 assumptions and limitations

- MOV is a container, not a codec. A valid upload may still use a codec a particular browser cannot play; transcoding belongs in the Phase 2 worker pipeline.
- A lightweight file signature check prevents renamed arbitrary files, but is not a malware scanner.
- There is no authentication in the single-user local MVP.
- Processing remains `uploaded`; no background worker is started in this phase.
- Monitoring directories are reserved for Phase 4. Redis and Celery are deliberately deferred until background analysis exists.

## Next phase

Phase 2 will add MediaPipe Pose Landmarker, configurable frame sampling, timestamped landmark persistence, missing-landmark handling, annotated video output, and fixture-based computer-vision tests. It should preserve the upload and API contracts established here.
