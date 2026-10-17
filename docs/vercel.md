# Deploy ClimbIQ on Vercel

ClimbIQ deploys as one Vercel project with two independently built services:

```text
https://<project>.vercel.app/*       -> frontend (Vite PWA)
https://<project>.vercel.app/api/*   -> backend (FastAPI)
                                            |
                                            +-- managed PostgreSQL
```

The browser calls the API through the public, same-origin `/api` path. There are no server-side
service-to-service calls, so `vercel.json` intentionally declares no service bindings. The
Vercel entrypoint also disables the reversible pose-analysis routes and worker; Docker and Render
keep that subsystem available.

## 1. Create the project and database

1. Import the GitHub repository into Vercel.
2. Set the project Framework Preset to **Services**. Vercel then reads the repository-root
   `vercel.json` and builds `frontend` and `backend` independently.
3. Create a managed PostgreSQL database through the Vercel Marketplace, Neon, Supabase, or
   another provider that supports TLS connections.
4. Add its pooled production connection string as `DATABASE_URL`. ClimbIQ accepts
   `postgres://`, `postgresql://`, or `postgresql+psycopg://` and selects the psycopg driver.

Use a separate database for preview deployments if previews will receive real test traffic.

## 2. Configure Google OAuth

Create a Google OAuth 2.0 Web application and register this exact production callback:

```text
https://<project>.vercel.app/api/auth/google/callback
```

If a custom domain is added later, add its callback in Google Cloud before switching the Vercel
environment variables.

## 3. Add production environment variables

Configure these values for the Vercel Production environment. Secrets must be entered in Vercel,
never committed to the repository.

| Variable | Production value |
| --- | --- |
| `DATABASE_URL` | Pooled PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | Google OAuth web client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `AUTH_ALLOWED_EMAILS` | Comma-separated private-beta accounts |
| `TOKEN_ENCRYPTION_KEY` | Random secret of at least 32 characters |
| `AUTH_REQUIRED` | `true` |
| `AUTH_COOKIE_SECURE` | `true` |
| `FRONTEND_URL` | `https://<project>.vercel.app` |
| `GOOGLE_REDIRECT_URI` | `https://<project>.vercel.app/api/auth/google/callback` |
| `CORS_ORIGINS` | `https://<project>.vercel.app` |
| `TRUSTED_HOSTS` | `<project>.vercel.app` |

The Vercel entrypoint defaults `ENVIRONMENT=production` and
`VIDEO_ANALYSIS_ENABLED=false`. Do not set a service binding URL or `VITE_API_URL`; the frontend's
production default is the same-origin `/api` path.

Generate `TOKEN_ENCRYPTION_KEY` with a password manager or another cryptographically secure
secret generator. Preview deployments need their own matching URLs and OAuth callback if Google
login is expected to work there.

## 4. Apply database migrations

Run migrations from a trusted machine before directing users to the deployment:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export DATABASE_URL='<pooled-postgres-connection-string>'
alembic upgrade head
```

Do not place `alembic upgrade head` in the frontend build or run it concurrently from multiple
preview builds. Apply migrations once for each target database.

## 5. Deploy and verify

Push to the production branch or run `npx vercel@latest --prod` from the repository root. Then:

1. Open `/api/health` and confirm `status` is `ok` and `database` is `connected`.
2. Sign in through Google using an allowlisted account.
3. Log one outdoor climb and one MoonBoard 2016/40° problem, then refresh and confirm both remain.
4. Import a small Mountain Project CSV and confirm a second import skips duplicates.
5. Install the PWA from Safari's **Share -> Add to Home Screen** action.
6. Confirm `/api/videos` returns `404`; pose analysis is not part of this deployment.

For local multi-service routing, install the Vercel CLI and run `vercel dev -L`. Normal feature
development can continue to use `docker compose up --build`.
