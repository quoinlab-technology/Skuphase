"""School Settings module (FRONTEND_SPEC sec 6.12 & UI_design/Settings.png).

Allows school administrators to configure school profile, academic sessions,
curriculum levels, and exam generation policies.
"""

import secrets
import logging

from fasthtml.common import (
    A,
    Div,
    Form,
    H1,
    P,
    Span,
    Strong,
    Title,
    to_xml,
    Img,
)
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from faststrap import (
    Button,
    Card,
    Col,
    EmptyState,
    Icon,
    Input,
    Row,
    Select,
    Spinner,
    Switch,
)

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.config.settings import get_settings
from app.services.school_logo_storage import delete_logo, upload_logo

logger = logging.getLogger(__name__)


def _owned_logo_path(school_id: str, path: str | None) -> str | None:
    """Only allow cleanup inside this school's logo prefix."""
    prefix = f"schools/{school_id}/logo/"
    return path if path and path.startswith(prefix) else None

# Audit2 Phase 2 — Settings → Notifications tab (mirrors prototype
# Settings.png–Settings6.png and NotificationPrefs schema defaults).
NOTIF_PREFS = [
    ("exam_generation_completed", "Exam generation completed",
     "Get notified when your exam finishes generating.", True),
    ("new_audit_comments", "New audit comments",
     "Know right away when a reviewer comments on your exam.", True),
    ("proposal_status_changes", "Exam workflow updates",
     "Follow generation and review updates for your exams.", True),
    ("document_processing_done", "Document processing completed",
     "Know when an uploaded curriculum or source document is ready.", True),
    ("user_joins_school", "User joins school",
     "Know when a new staff member joins your school.", False),
    ("preflight_check_failed", "Preflight check failed",
     "Alert me when a quality preflight check fails.", True),
]
NOTIF_PREF_KEYS = [key for key, *_ in NOTIF_PREFS]


async def _load_settings_context(req: Request, user: dict):
    """Fetch school data, settings, and notification preferences."""
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

    notif_state = {key: default for key, _, _, default in NOTIF_PREFS}
    r_prefs = await call_api(req, "GET", "/auth/me/preferences")
    ok_prefs, d_prefs = unwrap(r_prefs)
    if ok_prefs and isinstance(d_prefs.get("preferences"), dict):
        for key in NOTIF_PREF_KEYS:
            if key in d_prefs["preferences"]:
                notif_state[key] = bool(d_prefs["preferences"][key])

    return school_data, school_settings, notif_state


def _build_settings_content(
    user: dict,
    school_data: dict,
    school_settings: dict,
    notif_state: dict,
    active_tab: str = "profile",
    csrf_token: str | None = None,
):
    """Build the settings navigation and active tab body using native Faststrap components."""
    name = school_data.get("name") or user.get("school_name") or ("Personal Workspace" if user.get("account_type") == "individual_teacher" else "Your School")
    email = school_data.get("contact_email") or user.get("email") or ""
    phone = school_data.get("contact_phone") or school_data.get("phone") or ""
    state = school_data.get("state") or "Lagos"
    active_term = school_settings.get("active_term") or "First Term"
    academic_year = school_settings.get("academic_year") or "2025/2026"
    min_pass_mark = str(school_settings.get("min_pass_mark") or 50)
    address = school_data.get("address") or ""
    logo_url = school_settings.get("logo_url") or ""
    document_style = school_settings.get("document_style") or {}
    csrf_field = Input(name="csrf_token", value=csrf_token or "", type="hidden") if csrf_token else None

    def _tab_link(key: str, label: str, icon_name: str) -> A:
        is_curr = active_tab == key
        cls = "btn btn-sm rounded-pill px-3 py-2 fw-semibold me-2 mb-1 flex-shrink-0 " + (
            "btn-dark" if is_curr else "btn-outline-secondary"
        )
        return A(
            Icon(icon_name, cls="bi me-1"),
            label,
            href=f"/app/settings?tab={key}",
            cls=cls,
            hx_get=f"/ui/settings/tab?tab={key}",
            hx_target="#settings-content",
            hx_swap="outerHTML",
            hx_indicator="#settings-spinner",
            **({"aria-current": "true"} if is_curr else {}),
        )

    tabs_nav = Div(
        Div(
            _tab_link("profile", "School Profile", "building"),
            _tab_link("account", "My Account", "person"),
            _tab_link("notifications", "Notifications", "bell"),
            _tab_link("integrations", "API & Integrations", "plug"),
            _tab_link("policy", "Academic Policy", "mortarboard"),
            _tab_link("security", "Security", "shield-lock"),
            cls="d-flex flex-nowrap overflow-x-auto pb-2",
            style="scrollbar-width: none; -ms-overflow-style: none;",
        ),
        Div(
            Spinner(variant="success", size="sm", cls="me-2"),
            Span("Updating settings tab...", cls="small text-muted"),
            id="settings-spinner",
            cls="htmx-indicator mt-2",
        ),
        cls="mb-3",
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
            csrf_field,
            Strong("School Information", cls="fs-6 text-dark d-block mb-3"),
            Input("name", label="School Name", value=name, required=True),
            Row(
                Col(
                    Input("contact_email", input_type="email", label="Contact Email", value=email, required=True),
                    span=12,
                    md=6,
                ),
                Col(
                    Input("phone", label="Phone Number", value=phone),
                    span=12,
                    md=6,
                ),
                cls="g-3 mb-3",
            ),
            Strong("Exam document defaults", cls="fs-6 text-dark d-block mt-3 mb-2"),
            P("These settings apply to exam papers, marking guides, and OMR exports for all staff.", cls="text-muted small mb-2"),
            Row(
                Col(Input("doc_margin_mm", label="Page margin (mm)", value=str(document_style.get("margin_mm", 14)), input_type="number", min=8, max=30), span=12, md=4),
                Col(Input("doc_font_size", label="Body font size", value=str(document_style.get("font_size", 10)), input_type="number", min=8, max=14, step="0.5"), span=12, md=4),
                Col(Input("doc_question_spacing", label="Question spacing (mm)", value=str(document_style.get("question_spacing_mm", 2)), input_type="number", min=0, max=8, step="0.5"), span=12, md=4),
                cls="g-3 mb-3",
            ),
            Input("address", label="School Physical Address (Printed on Exam Papers)", value=address, placeholder="e.g. 15 Commercial Avenue, Yaba, Lagos"),
            Row(
                Col(
                    Select("state", *states, value=state, label="State / Region"),
                    span=12,
                    md=6,
                ),
                Col(
                    Div(
                        Input("logo_url", input_type="hidden", value=logo_url),
                    ),
                    span=12,
                    md=6,
                ),
                cls="g-3 mb-3",
            ),
            Div(
                Strong("Upload school logo", cls="small fw-semibold text-dark d-block mb-2"),
                P("PNG, JPG, or WebP · maximum 5 MB", cls="text-muted small mb-2"),
                Input("logo_file", input_type="file", accept="image/png,image/jpeg,image/webp", cls="form-control rounded-3", required=False),
                Button("Upload logo", type="submit", variant="outline-success", cls="rounded-pill px-3 mt-2"),
                action="/app/settings/logo-upload",
                method="post",
                enctype="multipart/form-data",
                cls="border rounded-3 p-3 bg-light-subtle mb-3",
                style="display:none;",
            ),
            Div(
                Button("Save School Profile", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold w-100 w-md-auto"),
                cls="d-flex justify-content-end mt-3",
            ),
            cls="p-4 border-0 shadow-sm rounded-4",
        ),
        action="/app/settings?tab=profile",
        method="post",
    )

    # Keep logo actions outside the profile form. This avoids invalid nested
    # multipart forms and gives the administrator a clear replace/reset flow.
    logo_preview = (
        Img(src=logo_url, alt=f"{name} school logo", cls="school-logo-preview img-fluid rounded-3")
        if logo_url
        else Div(
            Icon("image", cls="bi fs-1 text-muted"),
            Span("No logo uploaded", cls="small text-muted"),
            cls="school-logo-empty d-flex flex-column align-items-center justify-content-center",
        )
    )
    logo_actions = Card(
        Div(
            Div(
                Strong("School logo", cls="d-block text-dark"),
                P("This logo is used on school-generated documents.", cls="text-muted small mb-0"),
                cls="flex-grow-1",
            ),
            Span(
                "Uploaded" if logo_url else "Not set",
                cls=f"badge rounded-pill {'bg-success-subtle text-success' if logo_url else 'bg-light text-muted'}",
            ),
            cls="d-flex align-items-start justify-content-between gap-3 mb-3",
        ),
        Div(logo_preview, cls="school-logo-preview-wrap mb-3"),
        Form(
            csrf_field,
            Input("logo_file", input_type="file", accept="image/png,image/jpeg,image/webp", cls="form-control rounded-3", required=True),
            Div(
                P("PNG, JPG, or WebP · maximum 5 MB", cls="text-muted small mb-0"),
                Button(
                    "Replace logo" if logo_url else "Upload logo",
                    type="submit",
                    variant="success",
                    cls="btn-brand rounded-pill px-3",
                ),
                cls="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-2",
            ),
            action="/app/settings/logo-upload",
            method="post",
            enctype="multipart/form-data",
            cls="mb-2",
        ),
        (
            Button(
                "Reset logo",
                type="button",
                variant="outline-danger",
                cls="rounded-pill px-3",
                **{"data-bs-toggle": "modal", "data-bs-target": "#resetSchoolLogoModal"},
            )
            if logo_url
            else Div()
        ),
        cls="p-4 border-0 shadow-sm rounded-4 mt-3",
    )
    reset_logo_modal = Div(
        Div(
            Div(
                Div(
                    Strong("Reset school logo", cls="modal-title"),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0",
                ),
                Div(
                    P("This removes the current logo from school settings and Supabase Storage. You can upload a new logo afterwards.", cls="text-muted mb-0"),
                    cls="modal-body",
                ),
                Div(
                    Button("Cancel", type="button", variant="light", cls="rounded-pill px-4 me-2", **{"data-bs-dismiss": "modal"}),
                    Form(
                        csrf_field,
                        Button("Reset logo", type="submit", variant="danger", cls="rounded-pill px-4"),
                        action="/app/settings/logo-reset",
                        method="post",
                        cls="d-inline",
                    ),
                    cls="modal-footer border-0",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        id="resetSchoolLogoModal",
        cls="modal fade",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )
    profile_content = Div(profile_content, logo_actions, reset_logo_modal)

    # Tab 2: My Account
    account_content = Card(
        Strong("Account Information", cls="fs-6 text-dark d-block mb-3"),
        Row(
            Col(
                Input("user_name", label="Full Name", value=user.get("full_name", ""), readonly=True, cls="bg-light"),
                span=12,
                md=6,
            ),
            Col(
                Input("user_email", label="Email Address", value=user.get("email", ""), readonly=True, cls="bg-light"),
                span=12,
                md=6,
            ),
            cls="g-3 mb-3",
        ),
        Row(
            Col(
                Input("user_role", label="Role", value=(user.get("role") or "").replace("_", " ").title(), readonly=True, cls="bg-light"),
                span=12,
                md=6,
            ),
            Col(
                Input("user_account", label="Account Type", value=(user.get("account_type") or "").replace("_", " ").title(), readonly=True, cls="bg-light"),
                span=12,
                md=6,
            ),
            cls="g-3 mb-3",
        ),
        cls="p-4 border-0 shadow-sm rounded-4",
    )

    # Tab 3: Notifications
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
            csrf_field,
            Strong("Email & In-App Notifications", cls="fs-6 text-dark d-block mb-1"),
            P("Choose what SkuPhase tells you about. These preferences apply to your account only.",
              cls="text-muted small mb-3"),
            *notif_rows,
            Div(
                Button("Save Preferences", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold w-100 w-md-auto"),
                cls="d-flex justify-content-end mt-3",
            ),
            cls="p-4 border-0 shadow-sm rounded-4",
        ),
        action="/app/settings?tab=notifications",
        method="post",
    )

    # Tab 4: API & Integrations
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
        cls="p-4 border-0 shadow-sm rounded-4",
    )

    # Tab 5: Academic Policy
    policy_content = Form(
        Card(
            csrf_field,
            Strong("Academic Session & Policies", cls="fs-6 text-dark d-block mb-3"),
            Row(
                Col(
                    Input("academic_year", label="Current Academic Year", value=academic_year, placeholder="2025/2026"),
                    span=12,
                    md=6,
                ),
                Col(
                    Select("active_term", *terms, value=active_term, label="Active Term"),
                    span=12,
                    md=6,
                ),
                cls="g-3 mb-3",
            ),
            Input("min_pass_mark", input_type="number", label="Minimum Pass Mark (%)", value=min_pass_mark, min="1", max="100"),
            Div(
                Strong("National Curriculum Scope", cls="small fw-bold d-block mb-1"),
                P("Active: NERDC curriculum from Pre-Nursery through SSS 3. Primary, JSS, and SSS scheme-of-work data is available.", cls="text-muted small mb-0"),
                cls="p-3 rounded-3 bg-light border-start border-3 border-success mb-3",
            ),
            Div(
                Button("Save Academic Policies", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold w-100 w-md-auto"),
                cls="d-flex justify-content-end mt-3",
            ),
            cls="p-4 border-0 shadow-sm rounded-4",
        ),
        action="/app/settings?tab=policy",
        method="post",
    )

    # Tab 6: Security
    security_content = Div(
        Div(
            Div(Icon("shield-check", cls="bi fs-3 text-success me-3"), cls="d-flex align-items-center"),
            Div(
                Strong("Your account is secured", cls="d-block text-dark fw-bold"),
                Span("Password encryption and session tokens are active. We recommend using a unique password for SkuPhase.", cls="text-muted small"),
            ),
            cls="p-3 bg-light rounded-4 border d-flex align-items-center mb-4",
        ),
        Card(
            Strong("Change Password", cls="fs-6 text-dark d-block mb-3"),
            Form(
                csrf_field,
                Input("old_password", input_type="password", label="Current Password", required=True, placeholder="Enter current password"),
                Input("new_password", input_type="password", label="New Password", required=True, minlength="8", placeholder="At least 8 characters with uppercase and number"),
                Input("confirm_password", input_type="password", label="Confirm New Password", required=True, minlength="8", placeholder="Re-enter new password"),
                Div(
                    Button("Update Password", type="submit", variant="success", cls="btn-brand px-4 py-2 fw-semibold w-100 w-md-auto"),
                    cls="d-flex justify-content-end mt-3",
                ),
                action="/app/settings/change-password",
                method="post",
            ),
            cls="p-4 border-0 shadow-sm rounded-4",
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

    return Div(
        tabs_nav,
        active_content,
        id="settings-content",
        cls="pb-5 mb-5",
    )


def register_routes(app):
    # ------------------------------------------------------------------
    # HTMX partial: switch settings tab smoothly without reloading shell
    # ------------------------------------------------------------------
    @app.get("/ui/settings/tab")
    async def settings_tab_partial(req: Request, tab: str = "profile"):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        if role != "school_admin" and user.get("account_type") != "individual_teacher":
            return RedirectResponse("/app", status_code=303)

        school_data, school_settings, notif_state = await _load_settings_context(req, user)
        content = _build_settings_content(user, school_data, school_settings, notif_state, active_tab=tab.lower(), csrf_token=req.session.get("csrf"))
        push_url = f"/app/settings?tab={tab.lower()}"
        return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

    # ------------------------------------------------------------------
    # Full Page
    # ------------------------------------------------------------------
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
        active_tab = req.query_params.get("tab", "profile").lower()
        school_data, school_settings, notif_state = await _load_settings_context(req, user)

        # Support direct HTMX requests to /app/settings
        if req.headers.get("hx-request") or req.headers.get("HX-Request"):
            content = _build_settings_content(user, school_data, school_settings, notif_state, active_tab=active_tab, csrf_token=req.session.get("csrf"))
            return HTMLResponse(to_xml(content), headers={"HX-Push-Url": f"/app/settings?tab={active_tab}"})

        header = Div(
            H1("School Settings", cls="fw-bold fs-2 text-dark mb-1"),
            P("Configure school profile, academic sessions, security, and exam quality requirements.", cls="text-muted small mb-4"),
        )

        content = _build_settings_content(user, school_data, school_settings, notif_state, active_tab=active_tab, csrf_token=req.session.get("csrf"))

        return AppShell(
            Title("School Settings — SkuPhase"),
            Div(
                header,
                content,
            ),
            user=user,
            active="settings",
            flash=flash,
            crumbs=(
                [("Administration", "/app/admin"), ("School Settings", None)]
                if role == "school_admin"
                else [("School Settings", None)]
            ),
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
            payload: dict = {}
            if (form.get("name") or "").strip():
                payload["name"] = form.get("name").strip()
            if (form.get("contact_email") or "").strip():
                payload["contact_email"] = form.get("contact_email").strip()
            if (form.get("phone") or "").strip():
                payload["contact_phone"] = form.get("phone").strip()
            address_val = (form.get("address") or "").strip()
            state = (form.get("state") or "").strip()
            if address_val:
                payload["address"] = address_val
            elif state:
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

            logo_url_val = (form.get("logo_url") or "").strip()
            settings_payload = {
                "logo_url": logo_url_val,
                "document_style": {
                    "margin_mm": form.get("doc_margin_mm", 14),
                    "font_size": form.get("doc_font_size", 10),
                    "question_spacing_mm": form.get("doc_question_spacing", 2),
                },
            }
            await call_api(req, "PUT", f"/schools/{school_id}/settings", json=settings_payload)

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

    @app.post("/app/settings/logo-upload")
    async def upload_school_logo(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Only administrators can update school settings.", "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        school_id = user.get("school_id")
        form = await req.form()
        upload = form.get("logo_file")
        allowed_types = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        if not upload or not getattr(upload, "filename", None):
            push_flash(req, "Choose a logo file before uploading.", "warning")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        extension = allowed_types.get(getattr(upload, "content_type", ""))
        if not extension:
            push_flash(req, "Logo must be a PNG, JPG, or WebP image.", "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        content = await upload.read()
        if len(content) > 5 * 1024 * 1024:
            push_flash(req, "Logo must be 5 MB or smaller.", "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        settings = get_settings()
        object_path = f"schools/{school_id}/logo/{secrets.token_urlsafe(12)}{extension}"
        old_path = ""
        current_settings = await call_api(req, "GET", f"/schools/{school_id}/settings")
        current_ok, current_data = unwrap(current_settings)
        if current_ok:
            old_path = _owned_logo_path(school_id, current_data.get("logo_storage_path")) or ""
        try:
            logo_url = await upload_logo(
                settings,
                object_path,
                content,
                getattr(upload, "content_type", "application/octet-stream"),
            )
        except Exception:
            logger.exception("School logo upload failed for school_id=%s", school_id)
            push_flash(req, "The logo could not be uploaded to Supabase Storage.", "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)

        response = await call_api(
            req,
            "PUT",
            f"/schools/{school_id}/settings",
            json={"logo_url": logo_url, "logo_storage_path": object_path},
        )
        ok, data = unwrap(response)
        if not ok:
            try:
                await delete_logo(settings, object_path)
            except Exception:
                pass
            push_flash(req, data.get("message", "Could not save the uploaded logo."), "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        if old_path and old_path != object_path:
            try:
                await delete_logo(settings, old_path)
            except Exception:
                # The new logo is already canonical; an orphan cleanup can be
                # retried later without breaking the administrator workflow.
                pass
        session_user = req.session.get("user")
        if isinstance(session_user, dict):
            session_user["school_logo_url"] = logo_url
            req.session["user"] = session_user
        push_flash(req, "School logo uploaded successfully.", "success")
        return RedirectResponse("/app/settings?tab=profile", status_code=303)

    @app.post("/app/settings/logo-reset")
    async def reset_school_logo(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Only administrators can update school settings.", "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        school_id = user.get("school_id")
        settings = get_settings()
        current_response = await call_api(req, "GET", f"/schools/{school_id}/settings")
        ok, current = unwrap(current_response)
        old_path = _owned_logo_path(school_id, current.get("logo_storage_path")) if ok else None
        response = await call_api(
            req,
            "PUT",
            f"/schools/{school_id}/settings",
            json={"logo_url": None, "logo_storage_path": None},
        )
        saved, data = unwrap(response)
        if not saved:
            push_flash(req, data.get("message", "Could not reset the school logo."), "danger")
            return RedirectResponse("/app/settings?tab=profile", status_code=303)
        if old_path:
            try:
                await delete_logo(settings, old_path)
            except Exception:
                pass
        session_user = req.session.get("user")
        if isinstance(session_user, dict):
            session_user["school_logo_url"] = None
            req.session["user"] = session_user
        push_flash(req, "School logo reset. You can upload a new one at any time.", "success")
        return RedirectResponse("/app/settings?tab=profile", status_code=303)
