# ClimbIQ

ClimbIQ is an installable, account-based indoor bouldering analysis app. Phase 2 accepts climbing videos, runs MediaPipe Pose Landmarker, persists timestamped body landmarks, and produces an annotated review video alongside the original attempt. Google sign-in isolates each user's sessions, and users can separately authorize a read-only Gmail connection.

> **Phase boundary:** Phase 2 measures and visualizes pose. Joint-angle metrics, movement segmentation, and evidence-based technique observations remain Phase 3 work; the app does not invent technique verdicts from raw landmarks.

## Architecture

```text
Installable PWA (React + TypeScript + Vite + Tailwind)
              │ /api + HttpOnly session cookie
              ▼
FastAPI ── SQLAlchemy/Alembic ── PostgreSQL
   │                  │                 ▲
   │                  └── durable jobs ─┤ dedicated worker
   │                                    └── MediaPipe + OpenCV + FFmpeg
   └── private S3-compatible object storage (local disk in development)
```

Videos are stored outside PostgreSQL. Database rows keep metadata and storage keys, while normalized landmark samples are stored in PostgreSQL. The same processing interface supports a lightweight in-process executor for development and a durable database-backed worker for production.

In development, the API can run a lightweight in-process executor and use `data/videos/`. The
production Blueprint uses a separately scalable database-backed worker and private Cloudflare R2
storage with short-lived playback URLs.

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

Google OAuth is optional for zero-configuration local development. Without credentials, ClimbIQ
creates one local development account. Set `AUTH_REQUIRED=true` when testing the real login flow.

## Configure Google sign-in

Before starting the app:

1. Create or select a project in Google Cloud Console and configure its OAuth consent screen.
2. Enable the Gmail API.
3. Create an OAuth 2.0 Client ID with application type **Web application**.
4. Add `http://localhost:8000/api/auth/google/callback` as an authorized redirect URI.
5. Copy `.env.example` to `.env`, then set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and a unique `TOKEN_ENCRYPTION_KEY`.

Generate a suitable local encryption secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Google sign-in initially requests only `openid`, `email`, and `profile`. The separate **Connect Gmail** action requests `gmail.readonly`, stores access and refresh tokens encrypted at rest, and never grants ClimbIQ permission to send, modify, or delete mail. Public apps using this restricted Gmail scope must complete Google's applicable OAuth verification and security requirements.

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

The production-style worker can also be exercised locally:

```bash
PROCESSING_MODE=database docker compose --profile worker up --build
```

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
| `GET` | `/api/auth/me` | Read the current account and Gmail connection status |
| `GET` | `/api/auth/google/login` | Start Google sign-in with PKCE and state protection |
| `GET` | `/api/auth/google/callback` | Complete a Google login or Gmail authorization |
| `POST` | `/api/auth/logout` | Revoke the current browser session |
| `GET` | `/api/auth/gmail/connect` | Start the separate read-only Gmail authorization |
| `DELETE` | `/api/auth/gmail` | Revoke and remove the Gmail connection |
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

Copy `.env.example` to `.env` and adjust as needed. Do not commit `.env`, OAuth credentials, encryption keys, object-storage keys, or real climbing videos. `CORS_ORIGINS`, `TRUSTED_HOSTS`, and `AUTH_ALLOWED_EMAILS` accept comma-separated lists. Production configuration is fail-closed: it requires HTTPS URLs, secure cookies, Google OAuth, a private-beta email allowlist, and a strong durable encryption key. Changing `TOKEN_ENCRYPTION_KEY` invalidates stored Gmail tokens.

For hosting, use the checked-in `render.yaml` with private Cloudflare R2 storage. The complete
account setup, secret list, checklist, and smoke test are in
[`docs/deployment.md`](docs/deployment.md).

## Phase 2 assumptions and limitations

- MOV is a container, not a codec. The original may not play in every browser, but completed annotated output is transcoded to H.264.
- A lightweight file signature check prevents renamed arbitrary files, but is not a malware scanner.
- Existing unowned local sessions are assigned to the first account that signs in after the authentication migration; later users receive isolated empty workspaces.
- One climber is tracked per video. Occluded and off-screen landmarks are retained as missing data rather than guessed.
- Local mode is intentionally single-process. Production uses a database-backed worker that reclaims interrupted jobs and can scale independently from the API.
- The database queue is appropriate for private-beta volume. Redis/Celery and richer queue telemetry remain Phase 4 work if throughput requires them.

## Next phase

Phase 3 will derive joint angles, body alignment, movement intervals, and transparent heuristic observations from the stored landmark track. Those results should include confidence and evidence timestamps and remain descriptive rather than absolute judgments of correctness.
