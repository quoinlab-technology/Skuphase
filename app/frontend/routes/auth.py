"""Auth pages + handlers (FRONTEND_SPEC §6.1–6.3).

Full-page form posts with server-rendered flash feedback; tokens persist in
the signed session per §2.3.
"""

from fasthtml.common import (
    A, Div, Form, H1, H2, Label, Option, P, RedirectResponse,
    Script, Select, Span, Strong, Title,
)
from starlette.requests import Request
from starlette.datastructures import FormData

from faststrap import Button, Card, Col, Container, Icon, Input, Row

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


def _password_input_group(
    name, fid, label_text="Password", req=True, placeholder="Minimum 8 characters",
    err=None, toggle_id="toggle-pw", eye_id="eye-icon",
):
    base_cls = "form-control rounded-3 py-2 px-3 border-0 pe-5" + (" is-invalid" if err else "")
    return Div(
        Label(
            label_text,
            *([Span("*", cls="text-danger ms-1")] if req else []),
            cls="form-label text-muted small fw-medium mb-1",
            **{"for": fid},
        ),
        Div(
            Input(
                name,
                id=fid,
                input_type="password",
                placeholder=placeholder,
                required=req,
                cls=base_cls,
                style="background-color: #EDF2EC; font-size: 0.92rem;",
            ),
            Button(
                Icon("eye", cls="bi", id=eye_id),
                type="button",
                id=toggle_id,
                cls="btn border-0 position-absolute end-0 top-50 translate-middle-y me-2 text-muted p-1",
                style="background: transparent;",
            ),
            cls="position-relative",
        ),
        *([] if not err else [Span(err, cls="invalid-feedback d-block")]),
        cls="mb-3",
    )


def _login_form(email: str = ""):
    script = Script("""
    (function() {
      function init() {
        var togglePw = document.getElementById('login-toggle-pw');
        var pwInput = document.getElementById('login-password');
        var eyeIcon = document.getElementById('login-eye-icon');
        if (togglePw && pwInput && eyeIcon) {
          togglePw.onclick = function() {
            if (pwInput.type === 'password') {
              pwInput.type = 'text';
              eyeIcon.className = 'bi bi-eye-slash';
            } else {
              pwInput.type = 'password';
              eyeIcon.className = 'bi bi-eye';
            }
          };
        }
      }
      if (document.readyState !== 'loading') { init(); } else { document.addEventListener('DOMContentLoaded', init); }
    })();
    """)
    return Div(
        A("← Back to home", href="/", cls="text-decoration-none small text-muted mb-3 d-inline-block"),
        H1("Sign in to SkuPhase", cls="fw-bold text-dark mb-1", style="font-size: 1.85rem; letter-spacing: -0.02em;"),
        P("Enter your credentials to access your workspace.", cls="text-muted small mb-4"),
        Form(
            Div(
                Label("Email address", cls="form-label text-muted small fw-medium mb-1", **{"for": "login-email"}),
                Input(
                    "email",
                    id="login-email",
                    input_type="email",
                    value=email,
                    required=True,
                    placeholder="you@example.com",
                    cls="form-control rounded-3 py-2 px-3 border-0",
                    style="background-color: #EDF2EC; font-size: 0.92rem;",
                ),
                cls="mb-3",
            ),
            _password_input_group(
                "password", "login-password", label_text="Password", req=True,
                placeholder="Your password", toggle_id="login-toggle-pw", eye_id="login-eye-icon",
            ),
            Button(
                "Sign in",
                type="submit",
                variant="success",
                cls="btn btn-brand w-100 rounded-pill py-3 fw-semibold text-white shadow-sm mt-2",
                style="background-color: #00412E !important; border-color: #00412E !important; font-size: 0.95rem;",
            ),
            action="/login",
            method="post",
        ),
        P(
            A("Forgot password?", href="/forgot-password", cls="text-muted text-decoration-none"),
            " · ",
            A("Create an account", href="/register", cls="fw-semibold text-decoration-none", style="color: #00412E;"),
            cls="small text-center mt-4 mb-0",
        ),
        script,
    )


# ---------------------------------------------------------------- login


def register_session_routes(app):
    @app.get("/login")
    def login_page(req: Request, expired: str = "", registered: str = ""):
        flash = None
        if expired:
            clear_auth(req.session)
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


def _persona_tabs(mode: str = "school"):
    """Two-card persona selector matching prototype screenshot media_1788663171702.png (NO EMOJIS, real FastStrap icons)."""
    is_individual = mode == "individual"
    return Div(
        A("← Back to home", href="/", cls="text-decoration-none small text-muted mb-3 d-inline-block", id="auth-back-link"),
        Div(
            H1("Create your SkuPhase account", cls="fw-bold text-dark fs-3 mb-1"),
            P("Sign in to your workspace or register a new account.", cls="text-muted small mb-3"),
            cls="mb-3",
        ),
        Row(
            Col(
                A(
                    Div(
                        Icon("building", cls="bi fs-3 mb-2 d-block", style="color: #00412E;" if not is_individual else "color: #64748b;"),
                        Strong("School / Institution", cls="d-block text-dark small fw-bold mb-1"),
                        Span("Multi-teacher school", cls="text-muted", style="font-size: 0.78rem;"),
                        cls="p-3 text-center rounded-3 transition-all",
                        style=(
                            "background-color: #D6E4D8; border: 1.5px solid #00412E; box-shadow: 0 2px 8px rgba(0, 65, 46, 0.08);"
                            if not is_individual
                            else "background-color: #ffffff; border: 1px solid #CBD5E1;"
                        ),
                    ),
                    href="/register?mode=school",
                    cls="text-decoration-none d-block",
                ),
                span=6,
            ),
            Col(
                A(
                    Div(
                        Icon("person-fill", cls="bi fs-3 mb-2 d-block", style="color: #00412E;" if is_individual else "color: #64748b;"),
                        Strong("Individual Teacher", cls="d-block text-dark small fw-bold mb-1"),
                        Span("Solo / Private tutor", cls="text-muted", style="font-size: 0.78rem;"),
                        cls="p-3 text-center rounded-3 transition-all",
                        style=(
                            "background-color: #D6E4D8; border: 1.5px solid #00412E; box-shadow: 0 2px 8px rgba(0, 65, 46, 0.08);"
                            if is_individual
                            else "background-color: #ffffff; border: 1px solid #CBD5E1;"
                        ),
                    ),
                    href="/register?mode=individual",
                    cls="text-decoration-none d-block",
                ),
                span=6,
            ),
            g=3,
            cls="mb-4",
        ),
    )


def _field_group(label: str, input_el, fid: str, error: str | None = None):
    """Render a form-group with optional inline Bootstrap validation feedback."""
    return Div(
        Label(label, cls="form-label text-muted small fw-medium mb-1", **{"for": fid}),
        input_el if not error else Div(
            input_el,
            Span(error, cls="invalid-feedback d-block", id=f"{fid}-error"),
            cls="position-relative",
        ),
        cls="mb-3",
    )


def _individual_form(values: dict | None = None, field_errors: dict | None = None):
    v = values or {}
    e = field_errors or {}

    def _inp(name, fid, **kwargs):
        err = e.get(name) or e.get(f"body.{name}")
        base_cls = "form-control rounded-3 py-2 px-3 border-0" + (" is-invalid" if err else "")
        label_text = kwargs.pop("label", "")
        req = kwargs.get("required", False)
        style = kwargs.pop("style", "background-color: #EDF2EC; font-size: 0.92rem;")
        return Div(
            Label(
                label_text,
                *([Span("*", cls="text-danger ms-1")] if req else []),
                cls="form-label text-muted small fw-medium mb-1",
                **{"for": fid},
            ),
            Input(name, id=fid, cls=base_cls, style=style, **kwargs),
            *([] if not err else [Span(err, cls="invalid-feedback d-block")]),
            cls="mb-3",
        )

    progress_bar = Div(
        Div(style="height: 4px; border-radius: 4px; width: 100%; background-color: #00412E;"),
        cls="mb-4 w-100",
    )

    script = Script("""
    (function() {
      function init() {
        var togglePw = document.getElementById('ind-toggle-pw');
        var pwInput = document.getElementById('ind-password');
        var eyeIcon = document.getElementById('ind-eye-icon');
        if (togglePw && pwInput && eyeIcon) {
          togglePw.onclick = function() {
            if (pwInput.type === 'password') {
              pwInput.type = 'text';
              eyeIcon.className = 'bi bi-eye-slash';
            } else {
              pwInput.type = 'password';
              eyeIcon.className = 'bi bi-eye';
            }
          };
        }
      }
      if (document.readyState !== 'loading') { init(); } else { document.addEventListener('DOMContentLoaded', init); }
    })();
    """)

    return Div(
        Form(
            progress_bar,
            H1("Register as an Individual Teacher", cls="fw-bold text-dark mb-1", style="font-size: 1.85rem; letter-spacing: -0.02em;"),
            P("Set up your personal tutor / teacher workspace", cls="text-muted small mb-4"),
            _inp("full_name", "ind-full_name", label="Full name",
                 value=v.get("full_name", ""), required=True, placeholder="e.g. Amina Bello"),
            _inp("email", "ind-email", label="Email address",
                 input_type="email", value=v.get("email", ""), required=True, placeholder="you@example.com"),
            _password_input_group(
                "password", "ind-password", label_text="Password", req=True,
                placeholder="Minimum 8 characters",
                err=e.get("password"),
                toggle_id="ind-toggle-pw", eye_id="ind-eye-icon",
            ),
            _inp("workspace_name", "ind-workspace_name", label="Workspace name (optional)",
                 value=v.get("workspace_name", ""),
                 placeholder="e.g. Musa Tutorial Center — defaults to your name"),
            _inp("phone_number", "ind-phone_number", label="Phone number (optional)",
                 input_type="tel", value=v.get("phone_number", ""), placeholder="+234 801 000 0000"),
            Div(
                Input("agree_terms", id="ind-agree_terms", input_type="checkbox", required=True, checked=True,
                      cls="form-check-input me-2", style="accent-color: #00412E;"),
                Label("I agree to the Terms of Service and Privacy Policy", cls="form-check-label text-muted small", **{"for": "ind-agree_terms"}),
                cls="mb-4 d-flex align-items-center",
            ),
            Button("Create Teacher Account", type="submit", variant="success",
                   cls="btn btn-brand w-100 rounded-pill py-3 fw-semibold text-white shadow-sm mt-2",
                   style="background-color: #00412E !important; border-color: #00412E !important; font-size: 0.95rem;"),
            action="/register/individual",
            method="post",
        ),
        P(
            "Already have an account? ",
            A("Sign in", href="/login", cls="fw-semibold text-decoration-none", style="color: #00412E;"),
            cls="text-center text-muted small mt-4 mb-0",
        ),
        script,
    )


def _school_form(values: dict | None = None, field_errors: dict | None = None, is_step_2: bool = False):
    v = values or {}
    e = field_errors or {}

    def _inp(name, fid, **kwargs):
        err = e.get(name) or e.get(f"body.{name}") or e.get(f"admin_user.{name.replace('admin_', '')}")
        base_cls = "form-control rounded-3 py-2 px-3 border-0" + (" is-invalid" if err else "")
        label_text = kwargs.pop("label", "")
        req = kwargs.get("required", False)
        style = kwargs.pop("style", "background-color: #EDF2EC; font-size: 0.92rem;")
        return Div(
            Label(
                label_text,
                *([Span("*", cls="text-danger ms-1")] if req else []),
                cls="form-label text-muted small fw-medium mb-1",
                **{"for": fid},
            ),
            Input(name, id=fid, cls=base_cls, style=style, **kwargs),
            *([] if not err else [Span(err, cls="invalid-feedback d-block")]),
            cls="mb-3",
        )

    # Step 1: School details (media_1788662908327.png)
    step1_div = Div(
        H1("Register your school", cls="fw-bold text-dark mb-1", style="font-size: 1.85rem; letter-spacing: -0.02em;"),
        P("Step 1 of 2 — School details", cls="text-muted small mb-4"),
        _inp("school_name", "sch-school_name", label="School name",
             value=v.get("school_name", ""), required=True, placeholder="Greenfield Academy"),
        Row(
            Col(
                Div(
                    Label("State", cls="form-label text-muted small fw-medium mb-1", **{"for": "sch-state"}),
                    Select(
                        *[Option(st, value=st, selected=(v.get("state") == st or (not v.get("state") and st == "Lagos")))
                          for st in ("Lagos", "Abuja (FCT)", "Rivers", "Oyo", "Ogun", "Kano", "Kaduna", "Enugu", "Delta", "Edo", "Anambra", "Kwara", "Ondo", "Osun", "Plateau", "Cross River", "Akwa Ibom", "Imo", "Abia")],
                        cls="form-select rounded-3 py-2 px-3 border-0",
                        style="background-color: #EDF2EC; font-size: 0.92rem;",
                        name="state",
                        id="sch-state",
                    ),
                    cls="mb-3",
                ),
                span=6,
            ),
            Col(
                _inp("lga", "sch-lga", label="LGA",
                     value=v.get("lga", ""), placeholder="Victoria Island"),
                span=6,
            ),
            g=3,
        ),
        Div(
            Label("School type", cls="form-label text-muted small fw-medium mb-1", **{"for": "sch-school_type"}),
            Select(
                *[Option(st, value=st, selected=(v.get("school_type") == st or (not v.get("school_type") and st == "Private Primary")))
                  for st in ("Private Secondary", "Private Primary", "Public Secondary", "Public Primary", "Faith-Based / Mission", "Comprehensive")],
                cls="form-select rounded-3 py-2 px-3 border-0 mb-3",
                style="background-color: #EDF2EC; font-size: 0.92rem;",
                name="school_type",
                id="sch-school_type",
            ),
        ),
        _inp("contact_email", "sch-contact_email", label="School email address",
             input_type="email", value=v.get("contact_email", ""), required=True, placeholder="admin@yourschool.edu.ng"),
        _inp("contact_phone", "sch-contact_phone", label="Phone number",
             input_type="tel", value=v.get("contact_phone", ""), placeholder="+234 801 000 0000"),
        Div(
            Label("How did you hear about us?", cls="form-label text-muted small fw-medium mb-1", **{"for": "sch-referral_source"}),
            Select(
                *[Option(src, value=src, selected=(v.get("referral_source") == src or (not v.get("referral_source") and src == "Word of mouth")))
                  for src in ("Word of mouth", "Social Media", "School Association / NAPPS", "Search / Web", "Education Conference", "Other")],
                cls="form-select rounded-3 py-2 px-3 border-0 mb-4",
                style="background-color: #EDF2EC; font-size: 0.92rem;",
                name="referral_source",
                id="sch-referral_source",
            ),
        ),
        Button("Continue to admin setup →", type="button", id="btn-next-step",
               cls="btn btn-brand w-100 rounded-pill py-3 fw-semibold text-white shadow-sm mt-2",
               style="background-color: #00412E !important; border-color: #00412E !important; font-size: 0.95rem;"),
        id="school-step-1",
        cls="" if not is_step_2 else "d-none",
    )

    # Step 2: Admin user setup (media_1788663073935.png)
    step2_div = Div(
        H1("Set up your admin account", cls="fw-bold text-dark mb-1", style="font-size: 1.85rem; letter-spacing: -0.02em;"),
        P("Step 2 of 2 — Admin user", cls="text-muted small mb-4"),
        Row(
            Col(
                _inp("admin_first_name", "sch-admin_first_name", label="First name",
                     value=v.get("admin_first_name", ""), required=True, placeholder="Adaeze"),
                span=6,
            ),
            Col(
                _inp("admin_last_name", "sch-admin_last_name", label="Last name",
                     value=v.get("admin_last_name", ""), required=True, placeholder="Okafor"),
                span=6,
            ),
            g=3,
        ),
        Input("admin_full_name", id="sch-admin_full_name", input_type="hidden", value=v.get("admin_full_name", "")),
        _inp("admin_email", "sch-admin_email", label="Admin email",
             input_type="email", value=v.get("admin_email", ""), required=True, placeholder="adaeze@greenfield.edu.ng"),
        _inp("admin_job_title", "sch-admin_job_title", label="Job title",
             value=v.get("admin_job_title", ""), placeholder="Vice-Principal / Exam Officer"),
        _password_input_group(
            "admin_password", "sch-admin_password", label_text="Password", req=True,
            placeholder="Minimum 8 characters",
            err=e.get("admin_password") or e.get("admin_user.password") or e.get("password"),
            toggle_id="sch-toggle-pw", eye_id="sch-eye-icon",
        ),
        Div(
            Input("agree_terms", id="sch-agree_terms", input_type="checkbox", required=True, checked=True,
                  cls="form-check-input me-2", style="accent-color: #00412E;"),
            Label("I agree to the Terms of Service and Privacy Policy", cls="form-check-label text-muted small", **{"for": "sch-agree_terms"}),
            cls="mb-4 d-flex align-items-center",
        ),
        Button("Create School Account", type="submit", id="btn-submit-school",
               cls="btn btn-brand w-100 rounded-pill py-3 fw-semibold text-white shadow-sm mt-2",
               style="background-color: #00412E !important; border-color: #00412E !important; font-size: 0.95rem;"),
        id="school-step-2",
        cls="d-none" if not is_step_2 else "",
    )

    progress_bar = Div(
        Div(id="reg-bar-1", style="height: 4px; border-radius: 4px; flex: 1; background-color: #00412E;"),
        Div(
            id="reg-bar-2",
            style=f"height: 4px; border-radius: 4px; flex: 1; background-color: {'#00412E' if is_step_2 else '#CBD5E1'}; transition: background-color 0.2s ease;",
        ),
        cls="d-flex gap-2 mb-4 w-100",
    )

    script = Script("""
    (function() {
      function init() {
        var step1 = document.getElementById('school-step-1');
        var step2 = document.getElementById('school-step-2');
        var btnNext = document.getElementById('btn-next-step');
        var backLink = document.getElementById('auth-back-link');
        var bar2 = document.getElementById('reg-bar-2');
        var firstName = document.querySelector('input[name="admin_first_name"]');
        var lastName = document.querySelector('input[name="admin_last_name"]');
        var fullNameHidden = document.getElementById('sch-admin_full_name');

        function syncFullName() {
          if (firstName && lastName && fullNameHidden) {
            fullNameHidden.value = (firstName.value + ' ' + lastName.value).trim();
          }
        }

        if (btnNext && step1 && step2) {
          btnNext.onclick = function() {
            var schName = document.querySelector('input[name="school_name"]');
            var schEmail = document.querySelector('input[name="contact_email"]');
            if (schName && !schName.checkValidity()) {
              schName.reportValidity();
              return;
            }
            if (schEmail && !schEmail.checkValidity()) {
              schEmail.reportValidity();
              return;
            }
            step1.classList.add('d-none');
            step2.classList.remove('d-none');
            if (bar2) bar2.style.backgroundColor = '#00412E';
            if (backLink) {
              backLink.textContent = '← Back to school details';
              backLink.onclick = function(e) {
                e.preventDefault();
                step2.classList.add('d-none');
                step1.classList.remove('d-none');
                if (bar2) bar2.style.backgroundColor = '#CBD5E1';
                backLink.textContent = '← Back to home';
                backLink.onclick = null;
              };
            }
            syncFullName();
            if (firstName) firstName.focus();
          };
        }

        if (firstName) firstName.oninput = syncFullName;
        if (lastName) lastName.oninput = syncFullName;

        var togglePw = document.getElementById('sch-toggle-pw');
        var pwInput = document.getElementById('sch-admin_password');
        var eyeIcon = document.getElementById('sch-eye-icon');
        if (togglePw && pwInput && eyeIcon) {
          togglePw.onclick = function() {
            if (pwInput.type === 'password') {
              pwInput.type = 'text';
              eyeIcon.className = 'bi bi-eye-slash';
            } else {
              pwInput.type = 'password';
              eyeIcon.className = 'bi bi-eye';
            }
          };
        }
      }
      if (document.readyState !== 'loading') { init(); } else { document.addEventListener('DOMContentLoaded', init); }
    })();
    """)

    return Div(
        Form(
            progress_bar,
            step1_div,
            step2_div,
            action="/register/school",
            method="post",
        ),
        P(
            "Already have an account? ",
            A("Sign in", href="/login", cls="fw-semibold text-decoration-none", style="color: #00412E;"),
            cls="text-center text-muted small mt-4 mb-0",
        ),
        script,
    )


def register_routes(app):
    @app.get("/register")
    def register_page(req: Request, mode: str = "school"):
        mode = "individual" if mode == "individual" else "school"
        body = _individual_form() if mode == "individual" else _school_form()
        return AuthShell(
            _persona_tabs(mode),
            body,
            title="Create your SkuPhase account",
        )

    @app.get("/register/school")
    def register_school_page(req: Request):
        return AuthShell(
            _persona_tabs("school"),
            _school_form(),
            title="Create your SkuPhase account — School",
        )

    @app.get("/register/individual")
    def register_individual_page(req: Request):
        return AuthShell(
            _persona_tabs("individual"),
            _individual_form(),
            title="Create your SkuPhase account — Individual Teacher",
        )

    @app.post("/register/individual")
    async def register_individual_submit(req: Request):
        form = await req.form()
        values = {
            "full_name": _field(form, "full_name"),
            "email": _field(form, "email"),
            "workspace_name": _field(form, "workspace_name"),
            "phone_number": _field(form, "phone_number"),
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
        if values["phone_number"]:
            payload["phone_number"] = values["phone_number"]

        resp = await call_api(req, "POST", "/auth/register-individual", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            field_errors = data.get("fields", {}) if data.get("kind") == "validation" else {}
            top_msg = None if field_errors else data.get("message", "Registration failed. Please try again.")
            return AuthShell(
                _persona_tabs("individual"),
                Flash(top_msg, "danger") if top_msg else None,
                _individual_form(values, field_errors=field_errors),
                title="Create your SkuPhase account — Individual Teacher",
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
        first_name = _field(form, "admin_first_name")
        last_name = _field(form, "admin_last_name")
        full_name_raw = _field(form, "admin_full_name")
        admin_full_name = full_name_raw or (f"{first_name} {last_name}".strip() if (first_name or last_name) else "")

        state = _field(form, "state")
        lga = _field(form, "lga")
        address = f"{lga}, {state}".strip(", ") if (lga or state) else ""

        values = {
            "school_name": _field(form, "school_name"),
            "contact_email": _field(form, "contact_email"),
            "contact_phone": _field(form, "contact_phone"),
            "admin_first_name": first_name,
            "admin_last_name": last_name,
            "admin_full_name": admin_full_name,
            "admin_email": _field(form, "admin_email"),
            "admin_job_title": _field(form, "admin_job_title"),
            "state": state,
            "lga": lga,
            "school_type": _field(form, "school_type"),
            "referral_source": _field(form, "referral_source"),
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
        if address:
            payload["address"] = address

        resp = await call_api(req, "POST", "/auth/register", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            field_errors = data.get("fields", {}) if data.get("kind") == "validation" else {}
            top_msg = None if field_errors else data.get("message", "Registration failed. Please try again.")
            is_step_2 = any(
                k.startswith("admin_") or "password" in k or "user" in k or ("email" in k and "contact" not in k)
                for k in field_errors.keys()
            )
            return AuthShell(
                _persona_tabs("school"),
                Flash(top_msg, "danger") if top_msg else None,
                _school_form(values, field_errors=field_errors, is_step_2=is_step_2),
                title="Create your SkuPhase account — School",
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
