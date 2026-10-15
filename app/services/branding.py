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
        source_text = str(source)
        raw = get_logo_bytes(source_text)
        if raw is None:
            raise ValueError("school logo source is unavailable")
        from reportlab.platypus import Image
        return Image(io.BytesIO(raw), width=width, height=height, kind="proportional")
    except Exception as exc:
        # Do not fail the document because Supabase/CDN is temporarily
        # unavailable. Use the packaged local brand mark as a visible fallback.
        logger.warning(
            "School logo could not be loaded; using platform fallback (%s)",
            type(exc).__name__,
        )
        fallback_path = Path(__file__).resolve().parents[1] / "assets" / "img" / "skuphase_logo.png"
        if not fallback_path.is_file():
            return None
        try:
            from reportlab.platypus import Image
            return Image(str(fallback_path), width=width, height=height, kind="proportional")
        except Exception as fallback_exc:
            logger.error(
                "Platform logo fallback could not be rendered (%s)",
                type(fallback_exc).__name__,
            )
            return None


def get_logo_bytes(source: str | None) -> bytes | None:
    """Load a bounded image for export formats that need raw image bytes."""
    if not source:
        return None
    source_text = str(source)
    if source_text.startswith(("https://", "http://")):
        timeout = httpx.Timeout(4.0, connect=2.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(source_text)
            response.raise_for_status()
            if not response.headers.get("content-type", "").lower().startswith("image/"):
                raise ValueError("school logo URL did not return an image")
            if len(response.content) > MAX_LOGO_BYTES:
                raise ValueError("school logo exceeds the size limit")
            return _normalise_image_bytes(response.content)
    path = Path(source_text)
    if not path.is_file():
        raw_source = source_text.lstrip("/")
        for candidate in (Path(raw_source), Path("app") / raw_source, Path("assets") / raw_source):
            if candidate.is_file():
                path = candidate
                break
    if path.is_file() and path.stat().st_size <= MAX_LOGO_BYTES:
        return _normalise_image_bytes(path.read_bytes())
    return None


def _normalise_image_bytes(raw: bytes) -> bytes:
    """Validate supported school-logo formats and convert WebP for exports."""
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as image:
        image_format = image.format
        if image_format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("school logo must be PNG, JPEG, or WebP")
        if image.width * image.height > 20_000_000:
            raise ValueError("school logo dimensions exceed the export limit")
        image.load()
        if image_format != "WEBP":
            return raw
        normalized = io.BytesIO()
        image.convert("RGBA").save(normalized, format="PNG", optimize=True)
        value = normalized.getvalue()
        if len(value) > MAX_LOGO_BYTES:
            raise ValueError("converted school logo exceeds the export size limit")
        return value
