"""Generation Proposals module - RETIRED.

Teacher autonomy: teachers now generate exams directly via POST /exams/generate
(see app/api/v1/exams_router.py generation-proposal endpoints, which return 410
Gone). Browser navigations recover to the Exams page, while non-browser clients
receive 410 Gone so old integrations fail loudly instead of silently queuing
into a workflow that nobody reviews.

The reject route still forwards to the (now retired) backend reject endpoint so
that a reject can never trigger generation, and returns 410 regardless of the
backend response.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from app.frontend.api import call_api  # retained for compatibility with old integrations


def register_routes(app):
    """Register retired proposals routes - all return 410 Gone."""

    async def _retired(req: Request):
        # Browser routes should recover gracefully; API clients still receive
        # the explicit 410 responses from the backend endpoints.
        if req.url.path.startswith("/app/") and "text/html" in req.headers.get("accept", ""):
            return RedirectResponse("/app/exams?notice=Generation+proposals+are+retired.+Teachers+can+generate+directly.", status_code=303)
        return JSONResponse(
            status_code=410,
            content={
                "detail": (
                    "Generation proposals are retired. "
                    "Teachers can now generate exams directly from Exams."
                )
            },
        )

    # Register concrete paths before parameterised paths; Starlette preserves
    # declaration order and `/app/proposals/{proposal_id}` must not capture
    # the literal `new` path.
    retired_paths = [
        "/app/proposals",
        "/app/proposals/new",
        "/proposals",
        "/proposals/new",
        "/ui/proposals/list",
        "/app/proposals/{proposal_id}/accept",
        "/app/proposals/{proposal_id}",
        "/proposals/{proposal_id}",
        "/proposals/{proposal_id}/accept",
    ]

    for path in retired_paths:
        app.get(path)(_retired)
        app.post(path)(_retired)
        app.put(path)(_retired)
        app.delete(path)(_retired)

    async def proposal_generate_submit(req: Request, proposal_id: str):
        # Retired: generation from a proposal is disabled. Never triggers
        # exam generation - simply fail with 410 Gone.
        return await _retired(req)

    app.post("/app/proposals/{proposal_id}/generate")(proposal_generate_submit)
    app.post("/proposals/{proposal_id}/generate")(proposal_generate_submit)

    async def proposal_reject_submit(req: Request, proposal_id: str):
        # Retired: never make a pointless network request to another retired
        # endpoint; recover to the Exams page like the other browser routes.
        return await _retired(req)

    app.post("/app/proposals/{proposal_id}/reject")(proposal_reject_submit)
    app.post("/proposals/{proposal_id}/reject")(proposal_reject_submit)
