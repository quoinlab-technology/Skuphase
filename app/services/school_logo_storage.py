"""Supabase Storage operations for the single school branding logo."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.config.settings import Settings


def _base_url(settings: Settings) -> str:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase Storage is not configured")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object"


def public_logo_url(settings: Settings, object_path: str) -> str:
    return f"{_base_url(settings)}/public/{quote(settings.supabase_storage_bucket, safe='')}/{quote(object_path, safe='/')}"


async def upload_logo(settings: Settings, object_path: str, content: bytes, content_type: str) -> str:
    url = f"{_base_url(settings)}/{quote(settings.supabase_storage_bucket, safe='')}/{quote(object_path, safe='/')}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            url,
            content=content,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        response.raise_for_status()
    return public_logo_url(settings, object_path)


async def delete_logo(settings: Settings, object_path: str | None) -> None:
    if not object_path:
        return
    url = f"{_base_url(settings)}/{quote(settings.supabase_storage_bucket, safe='')}/{quote(object_path, safe='/')}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.delete(
            url,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
        # A missing old object should not block replacing/resetting the DB
        # setting; all other storage failures remain visible to the caller.
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()
