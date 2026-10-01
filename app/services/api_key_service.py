"""Creation and verification of tenant partner API keys."""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.api_key import ApiKey

ALLOWED_SCOPES = {"curriculum:read", "library:read", "diagram:render", "exams:read", "exams:create", "exports:read"}


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ApiKeyService:
    @staticmethod
    async def create(db: AsyncSession, school_id, name: str, scopes: list[str], quota_monthly: int, expires_at=None):
        invalid = sorted(set(scopes) - ALLOWED_SCOPES)
        if invalid:
            raise ValueError(f"Unknown API scope(s): {', '.join(invalid)}")
        secret = "sk_live_" + secrets.token_urlsafe(32)
        prefix = secret[:16]
        record = ApiKey(school_id=school_id, name=name.strip(), prefix=prefix, key_hash=hash_api_key(secret), scopes=sorted(set(scopes)), quota_monthly=quota_monthly, expires_at=expires_at)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record, secret

    @staticmethod
    async def verify(db: AsyncSession, raw_key: str, required_scope: str | None = None):
        if not raw_key or not raw_key.startswith("sk_"):
            return None
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key)))
        record = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not record or record.revoked_at or (record.expires_at and record.expires_at <= now):
            return None
        if required_scope and required_scope not in (record.scopes or []):
            return None
        record.last_used_at = now
        await db.commit()
        return record
