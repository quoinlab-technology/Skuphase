"""Resolve workspace-wide curriculum defaults for frontend workflows."""

from app.frontend.api import call_api, unwrap


async def workspace_curriculum_board(req, user: dict | None = None) -> str:
    """Return the configured source for this workspace.

    A missing settings row is a legacy installation and safely defaults to
    NERDC. Other API failures must not silently switch a configured workspace
    back to NERDC, which could put teachers on the wrong curriculum.
    """
    user = user or req.session.get("user") or {}
    school_id = user.get("school_id") or ""
    if school_id:
        response = await call_api(req, "GET", f"/schools/{school_id}/settings")
        ok, data = unwrap(response)
        if ok and isinstance(data, dict):
            board = str(data.get("curriculum_board") or "").strip()
            if board:
                return board
        if getattr(response, "status_code", None) != 404:
            raise RuntimeError("Unable to load the workspace curriculum setting")
    return "NERDC"
