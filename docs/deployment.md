# ClimbIQ deployment

The checked-in Render Blueprint deploys the private-beta production topology:

```text
HTTPS / installable PWA (climbiq-web)
          │ same-origin /api proxy
          ▼
Private FastAPI service (climbiq-api) ───── Render PostgreSQL
          │                                      ▲
          │ queues analysis jobs                 │ claims jobs
          ▼                                      │
Private Cloudflare R2 bucket ◀────────── pose worker (climbiq-worker)
```

The browser sees one HTTPS origin. The API is not exposed publicly, Google OAuth callbacks pass
through the web service, videos are private R2 objects, and short-lived signed URLs are used for
playback. Analysis runs outside the request process so an API restart cannot abandon queued jobs.

## Production-readiness checklist

- [x] Installable web manifest, icons, service worker, offline app shell, and update prompt
- [x] Multi-stage frontend image with Nginx SPA routing, API proxy, cache policy, and headers
- [x] Google login, secure server-side sessions, OAuth state binding, and private-beta allowlist
- [x] Per-user data isolation and optional read-only Gmail authorization
- [x] PostgreSQL migrations and startup health endpoint
- [x] Private S3-compatible video storage with short-lived playback URLs
- [x] Durable database queue and a separately scalable pose-processing worker
- [x] Render Blueprint for web, private API, worker, and PostgreSQL
- [x] Automated backend, frontend, and production-container checks
- [ ] Create the Cloudflare R2 bucket and credentials in your accounts
- [ ] Create the Google OAuth production client and consent-screen configuration
- [ ] Create the Render Blueprint, enter its secret variables, and run the release smoke test
- [ ] Add a custom domain, error monitoring, and a documented database recovery drill before a
  wider public launch

## 1. Create private object storage

1. In Cloudflare R2, create a private bucket such as `climbiq-videos`.
2. Create an R2 API token limited to reading and writing objects in that bucket.
3. Record the S3 endpoint shown by R2. It has the form
   `https://<account-id>.r2.cloudflarestorage.com`.
4. Keep the bucket private. Do not add a public development URL or public custom domain.

Render asks for the following values on both the API and worker services. Enter the same values
for each service:

| Variable | Value |
| --- | --- |
| `S3_ENDPOINT_URL` | The bucket's R2 S3 endpoint |
| `S3_BUCKET` | `climbiq-videos` (or your chosen bucket name) |
| `S3_ACCESS_KEY_ID` | R2 token access key ID |
| `S3_SECRET_ACCESS_KEY` | R2 token secret access key |

## 2. Create Google OAuth credentials

1. Configure the OAuth consent screen in Google Cloud.
2. Create an OAuth 2.0 client with application type **Web application**.
3. After Render creates the public web hostname, add this exact authorized redirect URI:
   `https://<climbiq-web-host>/api/auth/google/callback`.
4. The basic login asks only for identity scopes. The optional Gmail connection is a separate
   explicit grant and requests read-only Gmail access.

## 3. Deploy the Render Blueprint

1. Push the repository to GitHub and create a Render Blueprint from `render.yaml`.
2. Enter the R2 variables above for both `climbiq-api` and `climbiq-worker`.
3. For `climbiq-api`, set:
   - `FRONTEND_URL=https://<climbiq-web-host>`
   - `CORS_ORIGINS=https://<climbiq-web-host>`
   - `TRUSTED_HOSTS=<climbiq-web-host>`
   - `GOOGLE_REDIRECT_URI=https://<climbiq-web-host>/api/auth/google/callback`
   - `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from Google Cloud
   - `AUTH_ALLOWED_EMAILS` to the comma-separated accounts invited to the private beta
4. Sync the Blueprint again after the generated hostname is known.

Render generates the token-encryption key and database connection string. Never commit OAuth,
database, R2, or encryption secrets.

## 4. Verify the release

After the web, API, worker, and database report healthy:

1. Open the web URL over HTTPS and sign in with an allowlisted Google account.
2. Confirm `/api/health` reports `status: ok` and `/api/auth/me` reports the signed-in user.
3. Install ClimbIQ from Safari's **Share → Add to Home Screen** action or the install button in
   a Chromium browser.
4. Upload a small MP4. Confirm its state advances from queued to processing to completed and that
   both the original and annotated videos play.
5. Restart the API while another test video is queued. Confirm the worker still completes it.
6. Confirm an anonymous request to `/api/videos` receives `401`.
7. Confirm objects in R2 are private and their playback URLs expire.
8. Review Render database backups, service alerts, R2 retention, and expected monthly spend.

## Local worker mode

The default local stack processes jobs inside the API and needs no extra service:

```sh
docker compose up --build
```

To exercise the production-style database worker locally, stop the stack and run:

```sh
PROCESSING_MODE=database docker compose --profile worker up --build
```

Both modes use the same database records. Local storage remains the default unless
`STORAGE_BACKEND=s3` and the S3 variables are supplied.

## Scaling and operations

The API is stateless apart from temporary upload files. Add API or worker instances independently
after measuring queue time, CPU, memory, and database load. Do not expose the private API or make
the R2 bucket public. For a broader launch, add application error reporting, uptime checks, abuse
controls, lifecycle/retention rules, and a tested restore procedure.
