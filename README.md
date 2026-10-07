# SkuPhase

Curriculum-first AI exam generation for Nigerian primary schools.
Coverage: **Pre-Nursery – Primary 6** (NERDC scheme of work). JSS/SSS data is
planned but not yet ingested.

## How it works

```
Teacher picks class → subject → term → weeks
        ↓
Official NERDC scheme-of-work objectives   (indexed SQL lookup)
Curated few-shot past-question examples    (SQL lookup, platform corpus only)
        ↓
Single LLM call  (Groq llama-3.3-70b primary, OpenRouter fallback)
        ↓
Deterministic quality validator → persisted exam → review workflow → PDF export
```

**No ML runs on the server.** Embeddings, RAG, vector search and OCR were
deliberately removed (owner decision). The shared question corpus is seeded by
the owner via a local script; school-contributed questions never leave their
school's scope.

## Architecture as built

- **Backend**: FastAPI, ~55 API operations under `/api/v1/` (auth, users,
  schools, exams, ops, curriculum)
- **DB**: PostgreSQL + SQLAlchemy 2 async + Alembic (single squashed baseline:
  `0001_baseline_squash`)
- **Jobs**: Postgres-backed durable queue (`generation_jobs`) with an in-app
  asyncio worker (`FOR UPDATE SKIP LOCKED`) — survives restarts, safe with
  multiple app instances. Transient provider errors retry with backoff;
  validation/parse failures fail fast without burning extra LLM calls.
- **Storage**: local disk under `exports/exams/{exam_id}/`; downloads go
  through tenant-checked endpoints. Upload subsystem intentionally removed in
  v1 (returns as a clean module later).
- **Email**: provider abstraction — Gmail SMTP (App Password) today, Resend by
  flipping `MAIL_PROVIDER=resend` once the domain is verified.

## Roles & access (dual mode)

| Action | School admin | Individual teacher | Teacher/auditor (school staff) |
|---|---|---|---|
| Propose generation | ✓ | n/a (direct) | ✓ |
| Generate / refine / export / delete | ✓ | ✓ (own workspace) | ✗ (proposals only) |
| Submit final draft | ✓ | ✓ (self-approve) | own exams only |
| Approve | ✓ | ✓ (self) | ✗ |
| Browse/save question bank | ✓ | ✓ | teacher ✓ |

Manual exam submission (`POST /exams/manual-submit`) lets teachers write
papers without any AI involvement.

## Quick start

```powershell
git clone <repo> && cd skuphase
.\scripts\bootstrap_dev.ps1      # docker postgres, .env, deps, migrate, seed
venv\Scripts\python.exe run_server.py
```

Manual path: copy `.env.example` → `.env`, fill secrets, then
`alembic upgrade head`, seed curriculum, `run_server.py`.

### Environment notes

- `DATABASE_URL` must use the asyncpg driver:
  `postgresql+asyncpg://user:pass@host:5432/db`
- `CORS_ORIGINS` accepts a JSON array or comma-separated string.
- LLM vars are `GROQ_API_KEY` / `GROQ_BASE_URL` (Groq, not "Grok").
- Email MVP: create a Gmail App Password (2FA required), set `SMTP_USER` /
  `SMTP_PASSWORD`. Limit ≈500 sends/day — fine for pilots.

## Seeding & curation

```bash
# Curriculum (3,081 week rows, committed at data/)
python -m app.scripts.seed_curriculum_postgres --check   # offline dry-run
python -m app.scripts.seed_curriculum_postgres           # bulk upsert

# Platform few-shot corpus (owner-curated ONLY — see CP4 policy in
# docs/archive/AUDIT_REMEDIATION_PLAN.md §1; do NOT ingest verbatim WAEC/NECO papers)
python -m app.scripts.ingest_platform_questions --input my_items.json --dry-run
python -m app.scripts.ingest_platform_questions --input my_items.json
```

## Ops runbook

- **Supabase free tier**: pauses after ~1 week idle. `.github/workflows/
  keepalive.yml` pings `/api/v1/ops/health` every 2 days (set repo secret
  `SKUPHASE_HEALTH_URL`). Watch the 500 MB size ceiling.
- **Backups**: no PITR on free tier — `backup.yml` dumps nightly to private
  artifacts (set `SKUPHASE_BACKUP_DATABASE_URL`). Restore:
  `gunzip -c dump.sql.gz | psql "$DATABASE_URL"`.
- **Deploy**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`.
  Migrations run once per environment (`init_db.py` refuses unmigrated DBs).

## Development

```bash
pytest tests -q          # unit suite (no DB needed)
ruff check app tests
```

Integration tests against real Postgres: set `TEST_DATABASE_URL`, run a
scratch DB, `pytest -m integration`.

See `docs/archive/AUDIT_REMEDIATION_PLAN.md` for the historical security/completeness audit this code
line implements and the decisions behind it.
