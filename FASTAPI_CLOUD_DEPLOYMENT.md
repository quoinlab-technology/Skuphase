# SkuPhase FastAPI Cloud deployment runbook

FastAPI Cloud is the target for the pilot deployment. This runbook prepares the
existing FastAPI + FastHTML application for deployment; the actual deployment
must be initiated from an authenticated developer workstation.

## 1. Pre-deployment checks

Run from the `skuphase` directory:

```powershell
python -m compileall app tests
pytest -q tests --disable-warnings --maxfail=1
python -c "from app.main import app; print(app.title, len(app.routes))"
```

The configured FastAPI entrypoint is `app.main:app`. The application startup
lifespan verifies the database and starts the Postgres-backed generation worker.

## 2. Required production environment

Configure these values in FastAPI Cloud secrets/environment settings. Never
commit the real values:

- `APP_ENV=production`
- `DEBUG=false`
- `DATABASE_URL` using the `postgresql+asyncpg://` driver
- `JWT_SECRET_KEY` (a new random value, at least 32 characters)
- `GROQ_API_KEY` and/or `OPENROUTER_API_KEY`
- `MAIL_PROVIDER`, `MAIL_FROM`, and the selected SMTP/Resend credentials
- `APP_BASE_URL` set to the deployed HTTPS URL
- `CORS_ORIGINS` containing only the deployed UI/origins that need API access
- `ENABLE_SWAGGER=false` unless protected API documentation is intentionally
  required during the pilot

The deployment must use a managed PostgreSQL database reachable from the
FastAPI Cloud region. Run migrations against that database before opening the
application to pilot users:

```powershell
alembic upgrade head
```

Seed curriculum and other reference data only after checking the target
database URL and taking a backup.

## 3. Deploy

Install the project dependencies with the lock/requirements process used by the
deployment environment, authenticate with FastAPI Cloud, then run:

```powershell
uv run fastapi deploy
```

The first deployment will open browser authentication if the CLI session is not
already authenticated. Confirm the generated HTTPS URL before setting
`APP_BASE_URL` and any allowed CORS origin.

## 4. Pilot smoke test

After deployment, verify:

```text
GET /health
GET /login
GET /app/start
GET /docs                 (only if ENABLE_SWAGGER=true)
```

Then log in with a non-admin pilot account and verify the guided lesson,
classwork, exam, review/export, manual exam, worksheet PDF, and school-scoped
approval flows. Confirm that a generated PDF downloads successfully and that a
second request can still access its export.

## 5. Important operational boundary

SkuPhase currently stores generated exports and some uploaded assets on local
disk, and it runs the generation worker inside the application process. This is
appropriate for the initial persistent FastAPI Cloud pilot service, but those
paths must be moved to durable object storage and a separate worker/queue before
horizontal scaling or a serverless deployment model is introduced.

Do not run multiple independent production instances until the worker and local
file assumptions have been tested for duplicate processing and missing files.
