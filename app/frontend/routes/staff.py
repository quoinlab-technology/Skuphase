"""Staff and User Management module (FRONTEND_SPEC sec 6.11 & UI_design/Users.png).

Allows school administrators to invite teachers, assign roles, manage active status,
and review school access permissions.
"""

from urllib.parse import urlencode

from fasthtml.common import (
    A,
    Div,
    Form,
    H1,
    H2,
    Input as FTInput,
    Label,
    P,
    Span,
    Strong,
    Title,
    to_xml,
)
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from faststrap import (
    Alert,
    Badge,
    Button,
    Card,
    Col,
    Container,
    EmptyState,
    FormGroup,
    Icon,
    Input,
    Row,
    Select,
    Spinner,
)

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
                FTInput(type="hidden", name="target_active", value="false" if is_active else "true"),
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
                        Input("full_name", placeholder="e.g. Chinelo Okonkwo", label="Full Name", required=True),
                        Input("email", input_type="email", placeholder="teacher@school.edu.ng", label="Email Address", required=True),
                        Select("role", *roles, value="teacher", label="Role"),
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


def _render_staff_content(all_users: list, current_uid: str, status_filter: str = "", q: str = ""):
    """Build the filter pills, search bar, and staff table subtree."""
    # Counts
    counts = {
        "all": len(all_users),
        "active": sum(1 for u in all_users if u.get("is_active", True) and u.get("is_verified", True)),
        "invited": sum(1 for u in all_users if not u.get("is_verified", True)),
        "suspended": sum(1 for u in all_users if not u.get("is_active", True)),
    }

    # Filter
    filtered = all_users
    if q:
        filtered = [u for u in filtered if q in (u.get("full_name", "") + " " + u.get("email", "")).lower()]
    if status_filter == "active":
        filtered = [u for u in filtered if u.get("is_active", True) and u.get("is_verified", True)]
    elif status_filter == "invited":
        filtered = [u for u in filtered if not u.get("is_verified", True)]
    elif status_filter == "suspended":
        filtered = [u for u in filtered if not u.get("is_active", True)]

    def _pill(label: str, key: str):
        active_cls = " active" if status_filter == key else ""
        cnt = counts.get(key or "all", 0)
        href_query = f"/app/staff?status={key}" if key else "/app/staff"
        return A(
            f"{label} ({cnt})",
            href=href_query,
            cls=f"app-filter-pill{active_cls}",
            hx_get=f"/ui/staff/list?status={key}",
            hx_target="#staff-content",
            hx_swap="outerHTML",
            hx_include="#staff-filter-wrapper input",
            hx_indicator="#staff-spinner",
            onclick=f"const el=document.getElementById('staff-active-status'); if(el) el.value='{key}';",
        )

    pills = Div(
        _pill("All", ""),
        _pill("Active", "active"),
        _pill("Invited", "invited"),
        _pill("Suspended", "suspended"),
        cls="d-flex gap-2 flex-wrap mb-3",
    )

    search_bar = Div(
        Div(
            Icon("search", cls="bi text-muted position-absolute", style="top:0.75rem; left:1rem; font-size:1rem;"),
            FTInput(
                name="q",
                value=q,
                placeholder="Search staff by name or email...",
                cls="form-control rounded-pill ps-5 py-2 border shadow-sm",
                style="background:#fff;",
                id="staff-search-input",
                hx_get="/ui/staff/list",
                hx_target="#staff-content",
                hx_swap="outerHTML",
                hx_trigger="input changed delay:300ms, search",
                hx_include="#staff-filter-wrapper input",
                hx_indicator="#staff-spinner",
            ),
            cls="position-relative flex-grow-1",
            style="max-width: 580px;",
        ),
        Div(
            Spinner(variant="success", size="sm", cls="me-2"),
            Span("Updating staff list...", cls="small text-muted"),
            id="staff-spinner",
            cls="htmx-indicator ms-3 d-inline-flex align-items-center",
        ),
        id="staff-filter-wrapper",
        cls="d-flex flex-wrap align-items-center mb-4",
    )

    table_head = Div(
        Div("Name & Email", cls="col-md-4 fw-bold"),
        Div("Role", cls="col-md-2 text-md-center fw-bold"),
        Div("Status", cls="col-md-2 text-md-center fw-bold"),
        Div("Joined", cls="col-md-2 text-md-center fw-bold"),
        Div("Actions", cls="col-md-2 text-md-end fw-bold"),
        cls="row app-table-head g-0 d-none d-md-flex px-3 py-2 bg-light rounded-top-4 border-bottom text-muted small",
    )

    rows = [_user_row(u, current_uid) for u in filtered]

    if rows:
        table_container = Div(
            table_head,
            *rows,
            cls="app-table-container mb-4 shadow-sm bg-white rounded-4 border overflow-hidden",
        )
    elif not all_users:
        table_container = EmptyState(
            title="No staff members yet",
            description="Invite teachers and school administrators to collaborate on exam generation.",
            action=Button(
                Icon("plus-lg", cls="bi me-1"),
                "Invite Staff Member",
                type="button",
                variant="success",
                cls="btn-brand rounded-pill px-4",
                **{"data-bs-toggle": "modal", "data-bs-target": "#inviteUserModal"},
            ),
        )
    else:
        table_container = EmptyState(
            title="No staff members found",
            description="No staff match the current filters. Try changing your search query or selecting a different status filter.",
            action=Button(
                Icon("plus-lg", cls="bi me-1"),
                "Invite User",
                type="button",
                variant="success",
                cls="btn-brand rounded-pill px-4",
                **{"data-bs-toggle": "modal", "data-bs-target": "#inviteUserModal"},
            ),
        )

    return Div(
        FTInput(type="hidden", name="status", value=status_filter, id="staff-active-status"),
        pills,
        search_bar,
        table_container,
        id="staff-content",
        cls="pb-5 mb-5",
    )


def register_routes(app):
    # ------------------------------------------------------------------
    # HTMX partial: returns just #staff-content
    # ------------------------------------------------------------------
    @app.get("/ui/staff/list")
    async def staff_list_partial(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        if role != "school_admin" and user.get("account_type") != "individual_teacher":
            return RedirectResponse("/app", status_code=303)

        q = req.query_params.get("q", "").strip().lower()
        status_filter = req.query_params.get("status", "").strip()

        resp = await call_api(req, "GET", "/users/")
        ok, data = unwrap(resp)
        all_users = (data.get("users") or []) if ok else []
        if not all_users:
            all_users = [
                {
                    "id": user.get("user_id") or "self",
                    "full_name": user.get("full_name") or "Administrator",
                    "email": user.get("email") or "",
                    "role": role or "school_admin",
                    "is_active": True,
                    "is_verified": True,
                }
            ]

        content = _render_staff_content(all_users, user.get("user_id", ""), status_filter=status_filter, q=q)

        url_parts = []
        if status_filter:
            url_parts.append(f"status={status_filter}")
        if q:
            url_parts.append(f"q={q}")
        push_url = "/app/staff" + (f"?{'&'.join(url_parts)}" if url_parts else "")

        return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

    # ------------------------------------------------------------------
    # Full page
    # ------------------------------------------------------------------
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
        all_users = (data.get("users") or []) if ok else []

        if not all_users:
            all_users = [
                {
                    "id": user.get("user_id") or "self",
                    "full_name": user.get("full_name") or "Administrator",
                    "email": user.get("email") or "",
                    "role": role or "school_admin",
                    "is_active": True,
                    "is_verified": True,
                }
            ]

        # Support direct HTMX requests to /app/staff
        if req.headers.get("hx-request") or req.headers.get("HX-Request"):
            content = _render_staff_content(all_users, user.get("user_id", ""), status_filter=status_filter, q=q)
            url_parts = []
            if status_filter:
                url_parts.append(f"status={status_filter}")
            if q:
                url_parts.append(f"q={q}")
            push_url = "/app/staff" + (f"?{'&'.join(url_parts)}" if url_parts else "")
            return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

        total_users = len(all_users)
        teacher_cnt = sum(1 for u in all_users if (u.get("role") or "").lower() == "teacher")
        auditor_cnt = sum(1 for u in all_users if (u.get("role") or "").lower() == "auditor")
        admin_cnt = sum(1 for u in all_users if (u.get("role") or "").lower() == "school_admin")

        metrics = Row(
            Col(
                Div(
                    Div(Icon("people-fill", cls="bi"), cls="app-metric-icon-wrap icon-blue-light"),
                    Div(Div(str(total_users), cls="app-metric-value"), Div("Total Staff", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("mortarboard-fill", cls="bi"), cls="app-metric-icon-wrap icon-green-light"),
                    Div(Div(str(teacher_cnt), cls="app-metric-value"), Div("Teachers", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("shield-check", cls="bi"), cls="app-metric-icon-wrap icon-purple-light"),
                    Div(Div(str(auditor_cnt), cls="app-metric-value"), Div("Auditors", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=6, lg=3,
            ),
            Col(
                Div(
                    Div(Icon("gear-fill", cls="bi"), cls="app-metric-icon-wrap icon-amber-light"),
                    Div(Div(str(admin_cnt), cls="app-metric-value"), Div("Administrators", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=6, lg=3,
            ),
            cls="g-3 mb-4",
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
                cls="btn btn-brand rounded-pill px-4 py-2 text-white fw-semibold",
                style="background-color: #00412E !important; border: none;",
                **{"data-bs-toggle": "modal", "data-bs-target": "#inviteUserModal"},
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        staff_content = _render_staff_content(all_users, user.get("user_id", ""), status_filter=status_filter, q=q)

        return AppShell(
            Title("Users & Staff — SkuPhase"),
            Div(
                header,
                metrics,
                staff_content,
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
