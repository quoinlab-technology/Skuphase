"""Auth pages + handlers (FRONTEND_SPEC §6.1–6.3).

Full-page form posts with server-rendered flash feedback; tokens persist in
the signed session per §2.3.
"""

from fasthtml.common import A, Div, Form, H1, H2, Label, P, RedirectResponse, Title
from starlette.requests import Request
from starlette.datastructures import FormData

from faststrap import Button, Card, Input, Container

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import Flash, set_flash
from app.frontend.components.layout import AuthShell
from app.frontend.deps import clear_auth, store_auth

# ---------------------------------------------------------------- helpers


def _field(form: FormData, name: str) -> str:
    return (form.get(name) or "").strip()


def _form_error_page(title: str, error, email: str = ""):
    """Re-render an auth form with an error alert and preserved email."""
    return AuthShell(
        Flash(error["message"], variant="danger"),
        _login_form(email=email),
        title=title,
    )


def _login_form(email: str = ""):
    return Div(
        Form(
            Div(
                Label("Email address", cls="form-label"),
                Input(
                    "email",
                    input_type="email",
                    value=email,
                    required=True,
                    placeholder="you@example.com",
                    cls="form-control",
                ),
                cls="mb-3",
            ),
            Div(
                Label("Password", cls="form-label"),
                Input(
                    "password",
                    input_type="password",
                    required=True,
                    placeholder="Your password",
                    cls="form-control",
                ),
                cls="mb-3",
            ),
            Button("Sign in", type="submit", variant="success", cls="btn-brand w-100"),
            action="/login",
            method="post",
        ),
        P(
            A("Forgot password?", href="/forgot-password"),
            " · ",
            A("Create an account", href="/register"),
            cls="small text-center mt-3 mb-0",
        ),
    )


# ---------------------------------------------------------------- login


def register_session_routes(app):
    @app.get("/login")
    def login_page(req: Request, expired: str = "", registered: str = ""):
        flash = None
        if expired:
            flash = Flash("Your session expired — please sign in again.", "info")
        elif registered:
            flash = Flash("Account created — sign in below.", "success")
        return AuthShell(flash, _login_form(), title="Sign in to SkuPhase")

    @app.post("/login")
    async def login_submit(req: Request):
        form = await req.form()
        email = _field(form, "email")
        password = form.get("password") or ""

        resp = await call_api(req, "POST", "/auth/login", json={"email": email, "password": password})
        ok, data = unwrap(resp)
        if not ok:
            # 401 -> "Incorrect email or password." (no account enumeration)
            return AuthShell(Flash(data["message"], "danger"), _login_form(email=email), title="Sign in to SkuPhase")

        store_auth(req.session, data)
        return RedirectResponse("/app", status_code=303)

    async def _do_logout(req: Request):
        # Server-side refresh-token revocation (auth_router.logout); safe to
        # attempt even when the token is already dead.
        if req.session.get("access_token"):
            await call_api(req, "POST", "/auth/logout")
        clear_auth(req.session)
        set_flash(req.session, "info", "Signed out.")
        return RedirectResponse("/login", status_code=303)

    @app.post("/logout")
    async def logout_submit(req: Request):
        return await _do_logout(req)

    # Plain GET /logout (audit #6): the AppShell "Sign out" link is a plain
    # anchor, not a form POST — honour it instead of 405ing.
    @app.get("/logout")
    async def logout_link(req: Request):
        return await _do_logout(req)


# ---------------------------------------------------------------- register


async def _auto_login(req: Request, email: str, password: str) -> bool:
    """Login immediately after registration (§6.1 step 5)."""
    resp = await call_api(req, "POST", "/auth/login", json={"email": email, "password": password})
    ok, data = unwrap(resp)
    if ok:
        store_auth(req.session, data)
        return True
    return False


def _register_tabs(mode: str):
    individual_active = mode == "individual"
    return Div(
        A(
            "School",
            href="/register?mode=school",
            cls="btn btn-sm me-2 " + ("btn-success" if not individual_active else "btn-outline-secondary"),
        ),
        A(
            "I teach on my own",
            href="/register?mode=individual",
            cls="btn btn-sm " + ("btn-success" if individual_active else "btn-outline-secondary"),
        ),
        cls="mb-3 text-center",
    )


def _individual_form(values: dict | None = None):
    v = values or {}
    return Div(
        Form(
            Div(
                Label("Full name", cls="form-label"),
                Input("full_name", value=v.get("full_name", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("Email address", cls="form-label"),
                Input("email", input_type="email", value=v.get("email", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("Password", cls="form-label"),
                Input("password", input_type="password", required=True, cls="form-control"),
                Div("At least 8 characters.", cls="form-text"),
                cls="mb-3",
            ),
            Div(
                Label("Workspace name (optional)", cls="form-label"),
                Input(
                    "workspace_name",
                    value=v.get("workspace_name", ""),
                    placeholder="e.g. Musa Tutorial Center — defaults to your name",
                    cls="form-control",
                ),
                cls="mb-3",
            ),
            Button("Create my workspace", type="submit", variant="success", cls="btn-brand w-100"),
            action="/register/individual",
            method="post",
        ),
        P(A("Already have an account? Sign in", href="/login"), cls="small text-center mt-3 mb-0"),
    )


def _school_form(values: dict | None = None):
    v = values or {}
    return Div(
        Form(
            H2("School details", cls="app-section-title mt-2"),
            Div(
                Label("School name", cls="form-label"),
                Input("school_name", value=v.get("school_name", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("School contact email", cls="form-label"),
                Input("contact_email", input_type="email", value=v.get("contact_email", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("Phone (optional)", cls="form-label"),
                Input("contact_phone", value=v.get("contact_phone", ""), cls="form-control"),
                cls="mb-3",
            ),
            H2("Administrator account", cls="app-section-title mt-4"),
            Div(
                Label("Admin full name", cls="form-label"),
                Input("admin_full_name", value=v.get("admin_full_name", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("Admin email", cls="form-label"),
                Input("admin_email", input_type="email", value=v.get("admin_email", ""), required=True, cls="form-control"),
                cls="mb-3",
            ),
            Div(
                Label("Admin password", cls="form-label"),
                Input("admin_password", input_type="password", required=True, cls="form-control"),
                Div("At least 8 characters.", cls="form-text"),
                cls="mb-3",
            ),
            Button("Register school", type="submit", variant="success", cls="btn-brand w-100"),
            action="/register/school",
            method="post",
        ),
        P(A("Already have an account? Sign in", href="/login"), cls="small text-center mt-3 mb-0"),
    )


def register_routes(app):
    @app.get("/register")
    def register_page(req: Request, mode: str = "school"):
        mode = "individual" if mode == "individual" else "school"
        body = _individual_form() if mode == "individual" else _school_form()
        return AuthShell(
            _register_tabs(mode),
            body,
            title="Create your SkuPhase account",
        )

    @app.get("/register/school")
    @app.get("/register/individual")
    def register_mode_page(req: Request):
        # Audit #7: dedicated URLs so the two registration flows are linkable
        # and the wizard steps can't land users on the wrong form.
        path = req.url.path
        mode = "individual" if path.endswith("/individual") else "school"
        body = _individual_form() if mode == "individual" else _school_form()
        return AuthShell(
            _register_tabs(mode),
            body,
            title="Create your SkuPhase account",
        )

    @app.post("/register/individual")
    async def register_individual_submit(req: Request):
        form = await req.form()
        values = {
            "full_name": _field(form, "full_name"),
            "email": _field(form, "email"),
            "workspace_name": _field(form, "workspace_name"),
        }
        payload = {
            "full_name": values["full_name"],
            "email": values["email"],
            "password": form.get("password") or "",
        }
        if values["workspace_name"]:
            payload["workspace_name"] = values["workspace_name"]
        elif values["full_name"]:
            payload["workspace_name"] = f"{values['full_name']}'s Workspace"

        resp = await call_api(req, "POST", "/auth/register-individual", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return AuthShell(
                _register_tabs("individual"),
                Flash(_registration_error(data), "danger"),
                _individual_form(values),
                title="Create your SkuPhase account",
            )

        # Auto-login with the credentials just entered (§6.1 step 5).
        if await _auto_login(req, values["email"], payload["password"]):
            set_flash(req.session, "success", "Welcome to SkuPhase! Your workspace is ready.")
            return RedirectResponse("/app", status_code=303)
        set_flash(req.session, "success", "Account created — sign in below.")
        return RedirectResponse("/login?registered=1", status_code=303)

    @app.post("/register/school")
    async def register_school_submit(req: Request):
        form = await req.form()
        values = {
            "school_name": _field(form, "school_name"),
            "contact_email": _field(form, "contact_email"),
            "contact_phone": _field(form, "contact_phone"),
            "admin_full_name": _field(form, "admin_full_name"),
            "admin_email": _field(form, "admin_email"),
        }
        payload = {
            "school_name": values["school_name"],
            "contact_email": values["contact_email"],
            "admin_user": {
                "full_name": values["admin_full_name"],
                "email": values["admin_email"],
                "password": form.get("admin_password") or "",
            },
        }
        if values["contact_phone"]:
            payload["contact_phone"] = values["contact_phone"]

        resp = await call_api(req, "POST", "/auth/register", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return AuthShell(
                _register_tabs("school"),
                Flash(_registration_error(data), "danger"),
                _school_form(values),
                title="Create your SkuPhase account",
            )

        if await _auto_login(req, values["admin_email"], payload["admin_user"]["password"]):
            set_flash(req.session, "success", "School registered. You are signed in as administrator.")
            return RedirectResponse("/app", status_code=303)
        set_flash(req.session, "success", "School registered — sign in below.")
        return RedirectResponse("/login?registered=1", status_code=303)


def _registration_error(data: dict) -> str:
    """Map a registration failure to a single friendly message (§5.3)."""
    if data.get("kind") == "validation":
        fields = data.get("fields", {})
        for field, msg in fields.items():
            return f"{field.replace('_', ' ').capitalize()}: {msg}"
    return data.get("message", "Registration failed. Please try again.")


# ---------------------------------------------------------------- password reset


def register_more_routes(app):
    """Password reset, email verification and invite acceptance (§6.3)."""

    @app.get("/forgot-password")
    def forgot_password_page(req: Request):
        return AuthShell(
            Flash("If that email is registered, a reset link is on its way.", "success")
            if req.session.pop("_reset_sent", None)
            else None,
            Div(
                Form(
                    Div(
                        Label("Email address", cls="form-label"),
                        Input("email", input_type="email", required=True, cls="form-control"),
                        cls="mb-3",
                    ),
                    Button("Send reset link", type="submit", variant="success", cls="btn-brand w-100"),
                    action="/forgot-password",
                    method="post",
                ),
                P(A("Back to sign in", href="/login"), cls="small text-center mt-3 mb-0"),
            ),
            title="Reset your password",
        )

    @app.post("/forgot-password")
    async def forgot_password_submit(req: Request):
        form = await req.form()
        # Always the same response regardless of account existence (§6.3 —
        # no account enumeration).
        await call_api(
            req, "POST", "/auth/forgot-password", json={"email": _field(form, "email")}
        )
        req.session["_reset_sent"] = True
        return RedirectResponse("/forgot-password", status_code=303)

    @app.get("/reset-password")
    def reset_password_page(req: Request, token: str = ""):
        return AuthShell(
            _reset_password_form(token),
            title="Choose a new password",
        )

    @app.post("/reset-password")
    async def reset_password_submit(req: Request):
        form = await req.form()
        new_password = form.get("new_password") or ""
        confirm = form.get("confirm_password") or ""
        token = form.get("token") or ""
        if new_password != confirm:
            return AuthShell(
                Flash("The two passwords do not match.", "danger"),
                _reset_password_form(token),
                title="Choose a new password",
            )

        resp = await call_api(req, "POST", "/auth/reset-password", json={"token": token, "new_password": new_password})
        ok, data = unwrap(resp)
        if not ok:
            return AuthShell(
                Flash(data["message"], "danger"),
                P(A("Request a new link", href="/forgot-password"), cls="small text-center mb-0"),
                title="Choose a new password",
            )
        set_flash(req.session, "success", "Password updated — sign in with your new password.")
        return RedirectResponse("/login", status_code=303)


def _reset_password_form(token: str):
    return Form(
        Input("token", value=token, required=True, type="hidden"),
        Div(
            Label("New password", cls="form-label"),
            Input("new_password", input_type="password", required=True, cls="form-control"),
            Div("At least 8 characters.", cls="form-text"),
            cls="mb-3",
        ),
        Div(
            Label("Confirm new password", cls="form-label"),
            Input("confirm_password", input_type="password", required=True, cls="form-control"),
            cls="mb-3",
        ),
        Button("Update password", type="submit", variant="success", cls="btn-brand w-100"),
        action="/reset-password",
        method="post",
    )


def register_settlement_routes(app):
    """Email verification and invite acceptance (§6.3)."""

    @app.get("/verify-email")
    async def verify_email_page(req: Request, token: str = ""):
        if not token:
            return AuthShell(
                Flash("This verification link is incomplete.", "warning"),
                P(A("Resend verification email", href="/login"), cls="small text-center mb-0"),
                title="Verify your email",
            )
        resp = await call_api(req, "POST", "/auth/verify-email", json={"token": token})
        ok, data = unwrap(resp)
        if ok:
            set_flash(req.session, "success", "Email verified. Thank you!")
            return RedirectResponse("/app", status_code=303)
        return AuthShell(
            Flash("That verification link is invalid or has expired.", "warning"),
            P(A("Request a new link", href="/login"), cls="small text-center mb-0"),
            title="Verify your email",
        )

    # ------------------------------------------------------------ accept invite

    @app.get("/accept-invite")
    def accept_invite_page(req: Request, token: str = ""):
        return AuthShell(
            Form(
                Input("token", value=token, required=True, type="hidden"),
                Div(
                    Label("Your full name", cls="form-label"),
                    Input("full_name", cls="form-control"),
                    cls="mb-3",
                ),
                Div(
                    Label("Create a password", cls="form-label"),
                    Input("password", input_type="password", required=True, cls="form-control"),
                    Div("At least 8 characters.", cls="form-text"),
                    cls="mb-3",
                ),
                Button("Accept invitation", type="submit", variant="success", cls="btn-brand w-100"),
                action="/accept-invite",
                method="post",
            ),
            title="Join your school on SkuPhase",
        )

    @app.post("/accept-invite")
    async def accept_invite_submit(req: Request):
        form = await req.form()
        payload = {
            "token": form.get("token") or "",
            "password": form.get("password") or "",
        }
        full_name = _field(form, "full_name")
        if full_name:
            payload["full_name"] = full_name

        resp = await call_api(req, "POST", "/auth/accept-invite", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return AuthShell(
                Flash(
                    data.get("message", "This invitation is invalid or has expired.")
                    + " Ask your administrator to resend the invite.",
                    "danger",
                ),
                P(A("Back to sign in", href="/login"), cls="small text-center mb-0"),
                title="Join your school on SkuPhase",
            )
        set_flash(req.session, "success", "Invitation accepted — sign in with your new password.")
        return RedirectResponse("/login", status_code=303)
