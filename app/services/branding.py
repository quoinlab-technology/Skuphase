"""Shared school-branding helpers for generated documents."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)
MAX_LOGO_BYTES = 5 * 1024 * 1024


def logo_flowable(source: str | None, *, width, height):
    """Load a local or HTTPS logo into a bounded ReportLab image.

    Supabase Storage URLs are remote by design; ReportLab cannot render them
    directly, so the server fetches the image with a short timeout and keeps
    the bytes in memory only for the current export.
    """
    if not source:
        return None
    try:
        raw = None
        source_text = str(source)
        if source_text.startswith(("https://", "http://")):
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(source_text)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if not content_type.startswith("image/"):
                    raise ValueError("school logo URL did not return an image")
                if len(response.content) > MAX_LOGO_BYTES:
                    raise ValueError("school logo exceeds the size limit")
                raw = io.BytesIO(response.content)
        else:
            path = Path(source_text)
            if not path.is_file():
                raw_source = source_text.lstrip("/")
                for candidate in (Path(raw_source), Path("app") / raw_source, Path("assets") / raw_source):
                    if candidate.is_file():
                        path = candidate
                        break
            if path.is_file() and path.stat().st_size <= MAX_LOGO_BYTES:
                raw = str(path)
        if raw is None:
            return None
        from reportlab.platypus import Image
        return Image(raw, width=width, height=height)
    except Exception as exc:
        logger.warning("Failed to load school logo '%s': %s", source, exc)
        return None
