"""Resolve the workspace identity used on generated documents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentBranding:
    display_name: str
    logo_url: str | None


def resolve_document_branding(*, school, settings, user) -> DocumentBranding:
    """Use opted-in personal branding or the admin-managed school identity."""
    registered_name = (getattr(user, "full_name", None) or "").strip()
    workspace_name = (getattr(school, "name", None) or "").strip()
    custom_name = (getattr(settings, "document_display_name", None) or "").strip()
    logo_url = getattr(settings, "logo_url", None)

    if getattr(user, "account_type", None) == "individual_teacher":
        enabled = bool(getattr(settings, "personal_document_branding_enabled", False))
        return DocumentBranding(
            display_name=(custom_name or registered_name or workspace_name or "SkuPhase") if enabled else (registered_name or workspace_name or "SkuPhase"),
            logo_url=logo_url if enabled else None,
        )

    return DocumentBranding(
        display_name=custom_name or workspace_name or "SkuPhase",
        logo_url=logo_url,
    )
