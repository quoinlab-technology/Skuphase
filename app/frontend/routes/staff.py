"""Staff and User Management module (FRONTEND_SPEC sec 6.11 & UI_design/Users.png).

Allows school administrators to invite teachers, assign roles, manage active status,
and review school access permissions.
"""

from urllib.parse import urlencode
from fasthtml.common import A, Div, Form, H1, H2, Input, Label, P, Span, Strong, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Alert, Badge, Button, Card, Col, Container, EmptyState, FormGroup, Icon, Row, Select

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _role_badge(role: str) -> Span:
    r = (role or "teacher").lower()
    if r == "school_admin":
        return Span("Admin", cls="badge bg-dark text-white rounded-pill px-2 py-1 small")
    elif r == "auditor":
        return Span("Auditor", cls="badge bg-purple-subtle text-primary border border-primary-subtle rounded-pill px-2 py-1 small")
    return Span("Teacher", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1 small")


def _status_badge(is_active: bool, is_verified: bool = True) -> Span:
    if not is_active:
        return Span("Suspended", cls="badge bg-danger-subtle text-danger rounded-pill px-2 py-1 small")
    if not is_verified:
        return Span("Invited", cls="badge bg-warning-subtle text-warning-emphasis rounded-pill px-2 py-1 small")
    return Span("Active", cls="badge bg-success-subtle text-success rounded-pill px-2 py-1 small")


def _user_row(u: dict, current_uid: str) -> Div:
    uid = str(u.get("id") or u.get("user_id") or "")
    name = u.get("full_name") or "Staff Member"
    email = u.get("email") or ""
    role = u.get("role") or "teacher"
    is_active = u.get("is_active", True)
    is_verified = u.get("is_verified", True)
    created = (u.get("created_at") or "")[:10] or "Recent"
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "U"
    is_self = uid == current_uid

    actions = []
    if not is_self:
        actions.append(
            Form(
                # Pass the intended next state so the handler sends the correct
                # is_active value regardless of current DB state.
                Input(type="hidden", name="target_active", value="false" if is_active else "true"),
                Button(
                    "Deactivate" if is_active else "Activate",
                    type="submit",
                    variant="outline-danger" if is_active else "outline-success",
                    size="sm",
                    cls="rounded-pill py-1 px-3",
                ),
                action=f"/app/staff/{uid}/toggle-status",
                method="post",
                cls="d-inline",
            )
        )

    return Div(
        Div(
            Span(initials, cls="app-avatar me-3"),
            Div(
                Strong(name, cls="text-dark d-block mb-0 small"),
                Span(email, cls="text-muted small"),
                cls="text-truncate",
            ),
            cls="col-12 col-md-4 d-flex align-items-center mb-2 mb-md-0",
        ),
        Div(
            _role_badge(role),
            cls="col-6 col-md-2 text-md-center",
        ),
        Div(
            _status_badge(is_active, is_verified),
            cls="col-6 col-md-2 text-md-center",
        ),
        Div(
            Span(created, cls="small text-muted"),
            cls="col-6 col-md-2 text-md-center",
        ),
        Div(
            *actions,
            cls="col-6 col-md-2 text-md-end",
        ),
        cls="row app-table-row align-items-center g-0 px-3 py-3 border-bottom",
    )


def _invite_modal() -> Div:
    roles = [
        ("teacher", "Teacher — Can create, edit, and review exams"),
        ("auditor", "Auditor — Can audit questions, review quality, and leave comments"),
        ("school_admin", "School Admin — Full school administration and exam approval"),
    ]
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Invite New Staff Member", cls="fs-5 text-dark d-block"),
                        Span("Send an invitation email to join your school.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header pb-2",
                ),
                Form(
                    Div(
                        FormGroup("Full Name", Input("full_name", placeholder="e.g. Chinelo Okonkwo", cls="form-control", required=True), cls="mb-3"),
                        FormGroup("Email Address", Input("email", type="email", placeholder="teacher@school.edu.ng", cls="form-control", required=True), cls="mb-3"),
                        FormGroup("Role", Select("role", *roles, value="teacher", cls="form-select"), cls="mb-3"),
                        cls="modal-body py-2",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="outline-secondary", **{"data-bs-dismiss": "modal"}),
                        Button("Send Invitation", type="submit", variant="success", cls="btn-brand ms-2"),
                        cls="modal-footer pt-2",
                    ),
                    action="/app/staff/invite",
                    method="post",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="inviteUserModal",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def register_routes(app):
    @app.get("/app/staff")
    async def staff_list_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        if role != "school_admin" and user.get("account_type") != "individual_teacher":
            push_flash(req, "Access restricted to school administrators.", "danger")
            return RedirectResponse("/app", status_code=303)

        flash = pop_flash(req)
        q = req.query_params.get("q", "").strip().lower()
        status_filter = req.query_params.get("status", "").strip()

        resp = await call_api(req, "GET", "/users/")
        ok, data = unwrap(resp)
        user_list = (data.get("users") or []) if ok else []

        # If no users returned (e.g. backend initial state), display current user
        if not user_list:
            user_list = [
                {
                    "id": user.get("user_id") or "self",
                    "full_name": user.get("full_name") or "Administrator",
                    "email": user.get("email") or "",
                    "role": role or "school_admin",
                    "is_active": True,
                    "is_verified": True,
                }
            ]

        if q:
            user_list = [u for u in user_list if q in (u.get("full_name", "") + " " + u.get("email", "")).lower()]
        if status_filter == "active":
            user_list = [u for u in user_list if u.get("is_active", True) and u.get("is_verified", True)]
        elif status_filter == "invited":
            user_list = [u for u in user_list if not u.get("is_verified", True)]
        elif status_filter == "suspended":
            user_list = [u for u in user_list if not u.get("is_active", True)]

        total_users = len(user_list)
        teacher_cnt = sum(1 for u in user_list if (u.get("role") or "").lower() == "teacher")
        auditor_cnt = sum(1 for u in user_list if (u.get("role") or "").lower() == "auditor")
        admin_cnt = sum(1 for u in user_list if (u.get("role") or "").lower() == "school_admin")

        metrics = Row(
            Col(
                Div(
                    Div(Icon("people-fill", cls="bi"), cls="app-metric-icon-wrap icon-blue-light"),
                    Div(Div(str(total_users), cls="app-metric-value"), Div("Total Staff", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("mortarboard-fill", cls="bi"), cls="app-metric-icon-wrap icon-green-light"),
                    Div(Div(str(teacher_cnt), cls="app-metric-value"), Div("Teachers", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("shield-check", cls="bi"), cls="app-metric-icon-wrap icon-purple-light"),
                    Div(Div(str(auditor_cnt), cls="app-metric-value"), Div("Auditors", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("gear-fill", cls="bi"), cls="app-metric-icon-wrap icon-amber-light"),
                    Div(Div(str(admin_cnt), cls="app-metric-value"), Div("Administrators", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=6, lg=3,
            ),
            g=3,
            cls="mb-4",
        )

        header = Div(
            Div(
                H1("Users & Staff", cls="fw-bold fs-2 text-dark mb-1"),
                P("Manage school teachers, quality auditors, and administrator privileges.", cls="text-muted small mb-0"),
            ),
            Button(
                Icon("plus-lg", cls="bi me-1"),
                "Invite User",
                type="button",
                variant="success",
                cls="btn-brand px-3 py-2 fw-semibold",
                **{"data-bs-toggle": "modal", "data-bs-target": "#inviteUserModal"},
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        search_bar = Form(
            Div(
                Icon("search", cls="bi text-muted ms-2"),
                Input(name="q", value=q, placeholder="Search staff by name or email...", cls="form-control border-0 shadow-none"),
                Button("Search", type="submit", size="sm", cls="btn-brand me-1"),
                cls="d-flex align-items-center gap-2 app-card px-2 py-1 mb-3",
            ),
            method="get",
            action="/app/staff",
        )

        table_head = Div(
            Div("Name & Email", cls="col-md-4 fw-bold"),
            Div("Role", cls="col-md-2 text-md-center fw-bold"),
            Div("Status", cls="col-md-2 text-md-center fw-bold"),
            Div("Joined", cls="col-md-2 text-md-center fw-bold"),
            Div("Actions", cls="col-md-2 text-md-end fw-bold"),
            cls="row app-table-head g-0 d-none d-md-flex px-3",
        )

        rows = [_user_row(u, user.get("user_id", "")) for u in user_list]
        table_container = Div(table_head, *rows, cls="app-table-container mb-4")

        return AppShell(
            Title("Users & Staff — SkuPhase"),
            Div(
                header,
                metrics,
                search_bar,
                table_container,
                _invite_modal(),
            ),
            user=user,
            active="staff",
            flash=flash,
            crumbs=[("Users & Staff", None)],
        )

    @app.post("/app/staff/invite")
    async def invite_staff_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Only school administrators can invite staff members.", "danger")
            return RedirectResponse("/app/staff", status_code=303)

        form = await req.form()
        full_name = form.get("full_name", "").strip()
        email = form.get("email", "").strip()
        role = form.get("role", "teacher").strip()

        payload = {
            "email": email,
            "full_name": full_name,
            "role": role,
        }
        resp = await call_api(req, "POST", "/users/invite", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Failed to invite user."), "danger")
        else:
            push_flash(req, f"Invitation sent successfully to {email}.", "success")
        return RedirectResponse("/app/staff", status_code=303)

    @app.post("/app/staff/{user_id}/toggle-status")
    async def toggle_staff_status(req: Request, user_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Unauthorized.", "danger")
            return RedirectResponse("/app/staff", status_code=303)

        form = await req.form()
        # The _user_row button passes the intended *next* state via a hidden input
        # so we never have to guess the current state from the DB on this endpoint.
        target_active_str = (form.get("target_active") or "false").strip().lower()
        target_active = target_active_str == "true"

        resp = await call_api(req, "PUT", f"/users/{user_id}/status", json={"is_active": target_active})
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Failed to update user status."), "danger")
        else:
            action_word = "activated" if target_active else "deactivated"
            push_flash(req, f"User account {action_word} successfully.", "success")
        return RedirectResponse("/app/staff", status_code=303)
