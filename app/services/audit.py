"""Small, reusable audit-event writer with safe metadata boundaries."""

from app.core.request_context import get_request_id
from app.models.audit import AuditEvent


async def record_audit_event(
    db,
    *,
    actor_user_id=None,
    actor_role: str | None = None,
    school_id=None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    success: bool = True,
    summary: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    """Queue a sanitized event in the current transaction; never store secrets."""
    safe_metadata = dict(metadata or {})
    safe_metadata.pop("token", None)
    safe_metadata.pop("password", None)
    safe_metadata.pop("prompt", None)
    event = AuditEvent(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        school_id=school_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        success=success,
        request_id=get_request_id(),
        ip_address=ip_address,
        metadata_json=safe_metadata,
        summary=summary,
    )
    db.add(event)
    await db.flush()
    return event
