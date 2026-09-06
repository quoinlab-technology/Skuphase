"""School Settings module (FRONTEND_SPEC sec 6.12 & UI_design/Settings.png).

Allows school administrators to configure school profile, academic sessions,
curriculum levels, and exam generation policies.
"""

from fasthtml.common import A, Div, Form, H1, H2, Input, Label, P, Span, Strong, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import (
    Alert,
    Button,
    Card,
    Col,
    Container,
    EmptyState,
    FormGroup,
    Icon,
    Row,
    Select,
    Switch,
)

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login

# Audit2 Phase 2 — Settings → Notifications tab (mirrors prototype
# Settings.png–Settings6.png and NotificationPrefs schema defaults).
NOTIF_PREFS = [
    ("exam_generation_completed", "Exam generation completed",
     "Get notified when your exam finishes generating.", True),
    ("new_audit_comments", "New audit comments",
     "Know right away when a reviewer comments on your exam.", True),
    ("proposal_status_changes", "Proposal status changes",
     "Follow your proposal from request to generated exam.", True),
    ("document_processing_done", "Document processing done",
     "Alert me when uploaded documents finish processing.", False),
    ("user_joins_school", "User joins school",
     "Know when a new staff member joins your school.", False),
    ("preflight_check_failed", "Preflight check failed",
     "Alert me when a quality preflight check fails.", True),
]
NOTIF_PREF_KEYS = [key for key, *_ in NOTIF_PREFS]


def register_routes(app):
    @app.get("/app/settings")
    async def settings_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        if role != "school_admin" and user.get("account_type") != "individual_teacher":
            push_flash(req, "Access restricted to school administrators.", "danger")
            return RedirectResponse("/app", status_code=303)

        flash = pop_flash(req)
        school_id = user.get("school_id") or ""
        school_data = {}
        school_settings = {}

        if school_id:
            r1 = await call_api(req, "GET", f"/schools/{school_id}")
            ok1, d1 = unwrap(r1)
            if ok1:
                school_data = d1
            r2 = await call_api(req, "GET", f"/schools/{school_id}/settings")
            ok2, d2 = unwrap(r2)
            if ok2:
                school_settings = d2

        name = school_data.get("name") or user.get("school_name") or "Greenfield Academy"
        email = school_data.get("contact_email") or user.get("email") or ""
        phone = school_data.get("phone") or "+234 800 000 0000"
        state = school_data.get("state") or "Lagos"
        active_term = school_settings.get("active_term") or "First Term"
        academic_year = school_settings.get("academic_year") or "2025/2026"
        min_pass_mark = str(school_settings.get("min_pass_mark") or 50)

        active_tab = req.query_params.get("tab", "profile").lower()

        # Audit2 Phase 2: load saved notification preferences (schema defaults
        # apply to any key the user has never saved).
        notif_state = {key: default for key, _, _, default in NOTIF_PREFS}
        r_prefs = await call_api(req, "GET", "/auth/me/preferences")
        ok_prefs, d_prefs = unwrap(r_prefs)
        if ok_prefs and isinstance(d_prefs.get("preferences"), dict):
            for key in NOTIF_PREF_KEYS:
                if key in d_prefs["preferences"]:
                    notif_state[key] = bool(d_prefs["preferences"][key])

        header = Div(
            H1("School Settings", cls="fw-bold fs-2 text-dark mb-1"),
            P("Configure school profile, academic sessions, security, and exam quality requirements.", cls="text-muted small mb-4"),
        )

        def _tab_link(key: str, label: str, icon_name: str) -> A:
            is_curr = active_tab == key
            cls = "btn btn-sm rounded-pill px-3 py-2 fw-semibold me-2 mb-2 " + (
                "btn-dark" if is_curr else "btn-outline-secondary"
            )
            return A(Icon(icon_name, cls="bi me-1"), label, href=f"/app/settings?tab={key}", cls=cls,
                     **({"aria-current": "true"} if is_curr else {}))

        tabs_nav = Div(
            _tab_link("profile", "School Profile", "building"),
            _tab_link("account", "My Account", "person"),
            _tab_link("notifications", "Notifications", "bell"),
            _tab_link("integrations", "API & Integrations", "plug"),
            _tab_link("policy", "Academic Policy", "mortarboard"),
            _tab_link("security", "Security", "shield-lock"),
            cls="d-flex flex-wrap mb-4",
        )

        terms = [
            ("First Term", "First Term"),
            ("Second Term", "Second Term"),
            ("Third Term", "Third Term"),
        ]

        states = [
            ("Lagos", "Lagos State"),
            ("Abuja", "Abuja (FCT)"),
            ("Oyo", "Oyo State"),
            ("Rivers", "Rivers State"),
            ("Kaduna", "Kaduna State"),
            ("Enugu", "Enugu State"),
        ]

        # Tab 1: School Profile
        profile_content = Form(
            Card(
                Strong("School Information", cls="fs-6 text-dark d-block mb-3"),
                FormGroup("School Name", Input("name", value=name, cls="form-control", required=True), cls="mb-3"),
                Row(
                    Col(FormGroup("Contact Email", Input("contact_email", type="email", value=email, cls="form-control", required=True)), md=6),
                    Col(FormGroup("Phone Number", Input("phone", value=phone, cls="form-control")), md=6),
                    cls="mb-3",
                ),
                FormGroup("State / Region", Select("state", *states, value=state, cls="form-select"), cls="mb-3"),
                Div(
                    Button("Save School Profile", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold"),
                    cls="d-flex justify-content-end mt-3",
                ),
                cls="p-4 border-0 shadow-sm",
            ),
            action="/app/settings?tab=profile",
            method="post",
        )

        # Tab 2: My Account
        account_content = Card(
            Strong("Account Information", cls="fs-6 text-dark d-block mb-3"),
            Row(
                Col(FormGroup("Full Name", Input("user_name", value=user.get("full_name", ""), readonly=True, cls="form-control bg-light")), md=6),
                Col(FormGroup("Email Address", Input("user_email", value=user.get("email", ""), readonly=True, cls="form-control bg-light")), md=6),
                cls="mb-3",
            ),
            Row(
                Col(FormGroup("Role", Input("user_role", value=(user.get("role") or "").replace("_", " ").title(), readonly=True, cls="form-control bg-light")), md=6),
                Col(FormGroup("Account Type", Input("user_account", value=(user.get("account_type") or "").replace("_", " ").title(), readonly=True, cls="form-control bg-light")), md=6),
                cls="mb-3",
            ),
            cls="p-4 border-0 shadow-sm",
        )

        # Tab 3: Notifications (audit2 Phase 2 — matches prototype toggle list)
        notif_rows = []
        for key, title, desc, _default in NOTIF_PREFS:
            notif_rows.append(
                Div(
                    Switch(key, label=title, checked=notif_state.get(key, False),
                           label_cls="fw-semibold text-dark"),
                    P(desc, cls="text-muted small mb-0 ms-5"),
                    cls="py-2 border-bottom",
                )
            )
        notifications_content = Form(
            Card(
                Strong("Email & In-App Notifications", cls="fs-6 text-dark d-block mb-1"),
                P("Choose what SkuPhase tells you about. These preferences apply to your account only.",
                  cls="text-muted small mb-3"),
                *notif_rows,
                Div(
                    Button("Save Preferences", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold"),
                    cls="d-flex justify-content-end mt-3",
                ),
                cls="p-4 border-0 shadow-sm",
            ),
            action="/app/settings?tab=notifications",
            method="post",
        )

        # Tab 4: API & Integrations (audit2 Phase 2 — stub; backend is not
        # built yet, descope documented in FRONTEND_SPEC §6.12)
        integrations_content = Card(
            EmptyState(
                title="API access is coming soon",
                description=(
                    "School API keys and integrations (Google Drive, WAEC/NECO "
                    "standards) are on our roadmap. Contact your SkuPhase "
                    "representative to join the pilot."
                ),
                action=A(
                    Icon("envelope", cls="bi me-1"),
                    "Contact Support",
                    href="/about",
                    cls="btn btn-brand rounded-pill px-4",
                ),
            ),
            cls="p-4 border-0 shadow-sm",
        )

        # Tab 5: Academic Policy
        policy_content = Form(
            Card(
                Strong("Academic Session & Policies", cls="fs-6 text-dark d-block mb-3"),
                Row(
                    Col(FormGroup("Current Academic Year", Input("academic_year", value=academic_year, placeholder="2025/2026", cls="form-control")), md=6),
                    Col(FormGroup("Active Term", Select("active_term", *terms, value=active_term, cls="form-select")), md=6),
                    cls="mb-3",
                ),
                FormGroup("Minimum Pass Mark (%)", Input("min_pass_mark", type="number", value=min_pass_mark, min="1", max="100", cls="form-control"), cls="mb-3"),
                Div(
                    Strong("National Curriculum Scope", cls="small fw-bold d-block mb-1"),
                    P("Active: NERDC Primary School Curriculum (Pre-Nursery to Primary 6). All subjects and scheme of works seeded.", cls="text-muted small mb-0"),
                    cls="p-3 rounded bg-light border-start border-3 border-success mb-3",
                ),
                Div(
                    Button("Save Academic Policies", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold"),
                    cls="d-flex justify-content-end mt-3",
                ),
                cls="p-4 border-0 shadow-sm",
            ),
            action="/app/settings?tab=policy",
            method="post",
        )

        # Tab 4: Security (matching UI_design/Settings2.png)
        security_content = Div(
            Div(
                Div(Icon("shield-check", cls="bi fs-3 text-success me-3"), cls="d-flex align-items-center"),
                Div(
                    Strong("Your account is secured", cls="d-block text-dark fw-bold"),
                    Span("Password encryption and session tokens are active. We recommend using a unique password for SkuPhase.", cls="text-muted small"),
                ),
                cls="p-3 bg-light rounded-3 border d-flex align-items-center mb-4",
            ),
            Card(
                Strong("Change Password", cls="fs-6 text-dark d-block mb-3"),
                Form(
                    FormGroup("Current Password", Input("old_password", type="password", required=True, placeholder="Enter current password", cls="form-control mb-3")),
                    FormGroup("New Password", Input("new_password", type="password", required=True, minlength="8", placeholder="At least 8 characters with uppercase and number", cls="form-control mb-3")),
                    FormGroup("Confirm New Password", Input("confirm_password", type="password", required=True, minlength="8", placeholder="Re-enter new password", cls="form-control mb-3")),
                    Div(
                        Button("Update Password", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold"),
                        cls="d-flex justify-content-end mt-3",
                    ),
                    action="/app/settings/change-password",
                    method="post",
                ),
                cls="p-4 border-0 shadow-sm",
            ),
        )

        tab_bodies = {
            "profile": profile_content,
            "account": account_content,
            "notifications": notifications_content,
            "integrations": integrations_content,
            "policy": policy_content,
            "security": security_content,
        }
        active_content = tab_bodies.get(active_tab, profile_content)

        return AppShell(
            Title("School Settings — SkuPhase"),
            Div(
                header,
                tabs_nav,
                active_content,
            ),
            user=user,
            active="settings",
            flash=flash,
            crumbs=[("School Settings", None)],
        )

    @app.post("/app/settings/change-password")
    async def change_password_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        old_pwd = (form.get("old_password") or "").strip()
        new_pwd = (form.get("new_password") or "").strip()
        confirm_pwd = (form.get("confirm_password") or "").strip()

        if new_pwd != confirm_pwd:
            push_flash(req, "New passwords do not match.", "danger")
            return RedirectResponse("/app/settings?tab=security", status_code=303)

        resp = await call_api(req, "POST", "/auth/change-password", json={"old_password": old_pwd, "new_password": new_pwd})
        ok, data = unwrap(resp)
        if ok:
            push_flash(req, "Password updated successfully!", "success")
        else:
            push_flash(req, data.get("message", "Failed to update password."), "danger")
        return RedirectResponse("/app/settings?tab=security", status_code=303)

    @app.post("/app/settings")
    async def update_settings_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        form = await req.form()
        school_id = user.get("school_id") or ""
        target_tab = (req.query_params.get("tab") or "profile").lower()

        # Audit2 Phase 2: notification preferences are a per-user setting, so
        # individual teachers may save them too (handled before the
        # school-admin gate that protects school-wide tabs).
        if target_tab == "notifications":
            payload = {key: form.get(key) == "1" for key in NOTIF_PREF_KEYS}
            resp = await call_api(req, "PUT", "/auth/me/preferences", json=payload)
            ok, data = unwrap(resp)
            if ok:
                push_flash(req, "Notification preferences saved.", "success")
            else:
                push_flash(req, data.get("message", "Failed to save notification preferences."), "danger")
            return RedirectResponse("/app/settings?tab=notifications", status_code=303)

        if user.get("role") != "school_admin":
            push_flash(req, "Only administrators can update school settings.", "danger")
            return RedirectResponse("/app/settings", status_code=303)

        if school_id and target_tab == "profile":
            # Audit #8: "Save School Profile" previously fell through to the
            # policy handler and silently dropped name/email/phone/state.
            # Persist them via PUT /schools/{id} (SchoolUpdateRequest).
            payload: dict = {}
            if (form.get("name") or "").strip():
                payload["name"] = form.get("name").strip()
            if (form.get("contact_email") or "").strip():
                payload["contact_email"] = form.get("contact_email").strip()
            if (form.get("phone") or "").strip():
                payload["contact_phone"] = form.get("phone").strip()
            state = (form.get("state") or "").strip()
            if state:
                # The School model has no dedicated state column; keep it in
                # the free-form address field, preserving any other address text.
                resp = await call_api(req, "GET", f"/schools/{school_id}")
                ok, data = unwrap(resp)
                existing = data.get("address", "") if ok else ""
                kept = " ".join(
                    part for part in existing.split(" | ") if not part.startswith("State:")
                )
                parts = [p for p in (kept, f"State: {state}") if p]
                payload["address"] = " | ".join(parts)
            if payload:
                resp = await call_api(req, "PUT", f"/schools/{school_id}", json=payload)
                ok, data = unwrap(resp)
                if not ok:
                    push_flash(req, data.get("message", "Failed to save school profile."), "danger")
                    return RedirectResponse("/app/settings?tab=profile", status_code=303)
            push_flash(req, "School profile saved successfully.", "success")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)

        if school_id:
            payload = {
                "active_term": form.get("active_term", "First Term"),
                "academic_year": form.get("academic_year", "2025/2026"),
                "min_pass_mark": int(form.get("min_pass_mark", 50)) if form.get("min_pass_mark") else 50,
            }
            await call_api(req, "PUT", f"/schools/{school_id}/settings", json=payload)

        push_flash(req, "School settings saved successfully.", "success")
        return RedirectResponse("/app/settings", status_code=303)
