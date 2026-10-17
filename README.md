# ClimbIQ

ClimbIQ is an installable climbing logbook that brings outdoor routes and MoonBoard sessions into one account-owned timeline. Climbers can record sends and attempts, import their Mountain Project tick history, and see monthly progress across both disciplines.

## Current product

- Log outdoor routes and MoonBoard 2016 problems at 40° with grade, date, outcome, style, attempts, and notes.
- Classify outdoor climbs as sport, trad, boulder, top rope, multi-pitch, ice, or mixed.
- Import the official Mountain Project tick-list CSV without sharing a Mountain Project password.
- Re-import the same CSV safely; existing rows are detected and skipped.
- Filter one unified history by outdoor or MoonBoard climbing.
- Track total sends, climbing days, top grades, and monthly activity.
- Turn an outdoor objective into a project, tag its crux demands, and attach focused MoonBoard 2016/40° drills.
- Link project-related outdoor attempts and board sessions into one training-momentum signal with a suggested next action.
- Install the responsive React app as a PWA on iPhone, Android, or desktop.
- Keep every climb and log entry isolated to the signed-in Google account.

MoonBoard 2016 at 40° manual logging is available now. A searchable catalog is intentionally behind a data-source adapter while provider permission and catalog provenance are finalized. See [`docs/data-sources.md`](docs/data-sources.md).

## Architecture

```text
Installable PWA (React + TypeScript + Vite + Tailwind)
              │ /api + HttpOnly session cookie
              ▼
FastAPI ── SQLAlchemy/Alembic ── PostgreSQL
              │
              ├── unified climbs + logbook entries
              └── Mountain Project CSV importer
```

The previous pose-analysis tables and routes remain in the repository for a reversible migration, but they are no longer part of the product interface. A later cleanup can archive that subsystem once existing video data has been reviewed.

## Repository layout

```text
climbiq/
├── backend/           FastAPI app, SQLAlchemy models, Alembic, pytest
├── frontend/          React/Vite/Tailwind PWA
├── docs/              Data-source and deployment decisions
├── data/              Local runtime data (ignored by Git)
├── scripts/           Developer checks
└── docker-compose.yml Local PostgreSQL + app services
```

## Run locally

Docker is the quickest route:

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. With Google OAuth unset, local development uses the existing development-account fallback.

To run the services directly, use Python 3.12 and Node.js 22.12+:

```bash
docker compose up -d postgres

cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,video]'
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## API

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/health` | API and database readiness |
| `GET` | `/api/auth/me` | Current signed-in account |
| `GET` | `/api/logbook` | List the user's logbook entries |
| `POST` | `/api/logbook` | Record an outdoor or MoonBoard climb |
| `DELETE` | `/api/logbook/{id}` | Remove one logbook entry |
| `GET` | `/api/logbook/summary` | Totals and 12-month progress data |
| `POST` | `/api/logbook/import/mountain-project` | Import a Mountain Project tick CSV |
| `GET` | `/api/projects` | List outdoor projects, attached drills, and momentum |
| `POST` | `/api/projects` | Create an outdoor project |
| `POST` | `/api/projects/{id}/drills` | Attach a MoonBoard 2016/40° training problem |
| `PATCH` | `/api/projects/{id}` | Mark a project active, sent, or archived |

The importer expects Mountain Project's current 15-column tick export and caps uploads at 5 MB. It stores provider IDs and links when present but does not scrape route pages.

## Checks

```bash
./scripts/check.sh
```

This runs backend tests and linting plus frontend tests, type checking, and the production PWA build.

## Deploy on Vercel

The repository includes a two-service Vercel configuration for the current logbook product. It
serves the Vite PWA at `/` and FastAPI at `/api/*` on one origin. The legacy pose-analysis worker
is intentionally excluded from this deployment.

See [`docs/vercel.md`](docs/vercel.md) for the database, OAuth, environment-variable, migration,
and release steps.

## Next product slice

1. Finalize the licensed MoonBoard 2016/40° catalog source and attribution.
2. Add searchable MoonBoard problem selection and hold diagrams.
3. Add grade pyramids and personal-best milestones.
4. Add a user-owned JSON/CSV export for the complete ClimbIQ history.
5. Archive the legacy video-analysis deployment worker to reduce hosting cost.
