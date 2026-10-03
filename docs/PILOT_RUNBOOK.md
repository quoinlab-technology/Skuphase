# SkuPhase free-school pilot runbook

## Before onboarding a school

1. Apply migrations with `alembic upgrade head`.
2. Create the school administrator and verify the school ID in the session.
3. Confirm `/api/v1/ops/health` reports database health.
4. Run one manual exam, one generated exam, one lesson plan, and one worksheet export.
5. Record the school contact, pilot start date, and feedback owner outside the application.

## Daily checks

- Check `/api/v1/ops/health`.
- School administrators review `/api/v1/ops/stats` and `/api/v1/lesson-plans/coverage/summary`.
- Review failed generation jobs and export errors.
- Confirm backups completed and are readable.

## Backup and recovery

Run `scripts/backup_database.ps1` from the repository root with `DATABASE_URL` set.
Keep encrypted daily backups for 30 days and test one restore before every pilot
release. Never store backup files in the public assets directory.

## Incident response

1. Disable affected user accounts or revoke API keys.
2. Preserve the timestamp, school ID, request ID, and error details.
3. Do not copy student or teacher content into chat or issue trackers.
4. Restore to a new database for investigation; do not overwrite the live database.
5. Notify the pilot owner and affected school administrator.
