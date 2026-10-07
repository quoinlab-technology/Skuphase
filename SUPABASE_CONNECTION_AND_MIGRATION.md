# Supabase connection and migration runbook

SkuPhase uses SQLAlchemy async sessions at runtime and Alembic with the sync
driver for migrations. Keep two Supabase URLs in deployment secrets:

## Runtime URL

Use the **Transaction Pooler** URL from Supabase Connect (port `6543`) for the
FastAPI Cloud application when instances may scale or restart frequently:

```text
postgresql+asyncpg://postgres.<PROJECT_REF>:<PASSWORD>@<POOLER_HOST>:6543/postgres
```

The application already disables asyncpg prepared-statement caching for pooler
URLs. Do not put this value in git or in a browser-visible environment.

## Migration URL

Run Alembic with the **Session Pooler** URL (port `5432`) copied from the same
Supabase Connect dialog. It gives migration commands a stable database session:

```text
postgresql+asyncpg://postgres.<PROJECT_REF>:<PASSWORD>@<POOLER_HOST>:5432/postgres
```

Alembic removes `+asyncpg` automatically and uses the installed synchronous
PostgreSQL driver. Before the first live migration:

1. Make a Supabase backup/export and record the current `alembic_version`.
2. Set `DATABASE_URL` to the session-pooler URL in a private migration shell.
3. Run `alembic current`, then `alembic upgrade head`.
4. Run `alembic current` again and smoke-test login, curriculum, exam creation,
   PDF export, and email delivery.
5. Only then set the transaction-pooler URL as the FastAPI Cloud runtime secret.

For an IPv6-capable maintenance machine, Supabase also supports the direct
database URL on port `5432`; the session pooler is the safer default for an
IPv4-only workstation or CI runner.

## SMTP secrets

The current mailer expects these private environment variables:

```text
MAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<GMAIL_ADDRESS>
SMTP_PASSWORD=<GMAIL_APP_PASSWORD>
MAIL_FROM=<OPTIONAL_FROM_ADDRESS>
```

`SMTP_PASSWORD` must be a Gmail App Password, never the normal Gmail account
password. Rotate any password that has appeared in a local file, terminal
output, or chat, and keep `.env` out of commits. Resend can be enabled later by
switching `MAIL_PROVIDER=resend` and supplying `RESEND_API_KEY`.

Supabase connection mode guidance: transaction pooling is for application
runtime/serverless-style connections; session pooling or a direct connection is
for migrations and other operations that need a stable session.
