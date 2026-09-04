# SkuPhase Frontend Specification — FastHTML + Faststrap

**Version:** 1.0 · **Status:** Authoritative build specification
**Scope:** The complete server-rendered frontend for SkuPhase, served from the existing FastAPI application and deployed to FastAPI Cloud.
**Rule:** This document is the single source of truth for the frontend. Where it conflicts with older documents (e.g. `FRONTEND_END_TO_END_PROTOTYPE_PROMPT.md`, which describes deleted backend features), **this document wins**.

---

## 0. Sources of Truth (verified against the code, not assumed)

Every backend fact in this document was re-verified by reading the current code:

| Fact | Verified at |
| --- | --- |
| 6 routers mounted under `/api/v1` (auth, users, schools, exams, ops, curriculum) | `app/main.py:74-79` |
| Document upload / RAG / Assets subsystems **deleted** | routers no longer exist; old prototype prompt is stale |
| Auth endpoints incl. school + individual registration, cookie-able login | `app/api/v1/auth_router.py` |
| Exam lifecycle state machine + legal transitions | `app/core/workflow.py` |
| Dual-mode permissions (`individual_teacher` vs `school_staff`; roles `school_admin`/`teacher`/`auditor`) | `app/core/permissions.py`, `app/schemas/auth.py:183-192` |
| Exam generation is an **async job** (durable Postgres queue); UI must poll | `app/services/job_queue.py`, `ExamGenerationResponse.poll_endpoint` |
| Export returns `file_name` + `download_url`; download is tenant-scoped | `app/api/v1/exams_router.py:1800-1938` |
| 10 exams/day/school generation guard; 3 LLM calls per exam budget | `exams_router.py:220-231, 316-329` |
| Passages (comprehension), `language`, `true_false`, sub-parts supported | `app/schemas/exam.py:9-49`, migration `0003` |
| Installed frontend stack: `faststrap==0.8.2`, `python-fasthtml==0.14.9` | venv `pip list` (already installed) |
| Rate-limited login (Postgres-backed) returns 429 | `app/api/v1/auth_router.py:70-98` |
| **Visual reference: `UI_design/` screenshots (V0 prototype) are the design source of truth** — mapping + verdicts in §3.5. Nav items Documents/Assets/RAG Search in the screenshots are DEAD (deleted subsystems) and must never be built | §3.5 |

---

## 1. Product Framing

SkuPhase is an AI exam-generation platform for Nigerian primary schools. Its founding problem: **cut the cost, delay, and typing errors of producing exam papers.** Two first-class creation paths follow from that — and both must be visible from day one:

- **AI generation** — for teachers starting from the curriculum.
- **Manual entry** (`POST /exams/manual-submit`, already implemented in the backend) — for teachers who already have their questions; the platform typesets, checks, stores and exports them without any AI call. A teacher with existing questions is never blocked by the AI.

The frontend serves **two audiences with two workflow shapes**:

1. **Individual teachers** (`account_type == "individual_teacher"`): self-service. Generate → review → self-approve → export. No governance chain. This is the fast path and the pilot focus.
2. **Schools** (`account_type == "school_staff"`): governed. Teacher submits a generation *proposal* → school admin generates (owns the LLM budget) → teacher reviews/refines → teacher submits final → admin approves → export.

The backend permission model already implements both worlds (`is_workspace_admin()` is true for `school_admin` AND for individual teachers). The frontend branches **only** on navigation, dashboard content, and button visibility — never on separate code paths for permission checks (the API enforces everything server-side).

**Primary device target:** teacher laptops and Android phones. Mobile-first is mandatory, not optional.

---

## 2. Architecture

### 2.1 Serving model — one ASGI app

The FastHTML UI is mounted **inside the existing FastAPI app**. One process, one deploy, same-origin. API routes stay untouched at `/api/v1/*`.

```python
# app/main.py (addition, after API routers are included)
from faststrap import add_bootstrap, mount_assets
from app.frontend.app import frontend_app      # FastHTML instance

add_bootstrap(frontend_app, mode="light")      # exactly once, at startup
mount_assets(frontend_app, "assets")           # app-owned static -> /assets
app.mount("/", frontend_app)                   # LAST: API routes take precedence
```

Constraints (non-negotiable, from the faststrap skill):
- `add_bootstrap()` is called **once**, at startup — never per request.
- Faststrap reserves `/static` for framework assets. **All app-owned CSS/JS/images live in `assets/`** served from `/assets/...`. Never create app routes under `/static`.
- FastHTML translates `hx_post` → `hx-post`; always `cls=` (never `class=`); booleans for boolean attrs (`disabled=True`).
- No React, no Vue, no Alpine. HTMX (bundled) is the only interactivity layer.

### 2.2 In-process API client — the UI never talks to the DB directly

FastHTML route handlers must not create SQLAlchemy sessions or duplicate business rules. All data access goes through a thin async client that calls the app's **own API in-process** (no network hop, exact contract reuse, auth preserved):

```python
# app/frontend/api.py
from httpx import AsyncClient, ASGITransport

_transport = ASGITransport(app=app)   # the FastAPI app itself

async def api(request, method: str, path: str, **kwargs):
    """Forward the browser's auth session into an in-process API call."""
    headers = auth_headers_from_session(request)   # Bearer access token
    async with AsyncClient(transport=_transport, base_url="http://ui.local", headers=headers) as c:
        return await c.request(method, f"/api/v1{path}", **kwargs)
```

Rules:
- Handlers call `await api(req, "GET", "/exams")` and never build SQL or import models.
- Fallback (only if in-process forwarding proves awkward for an endpoint): call the existing service function with a short-lived `async_session_maker()` session. The client wrapper remains the only permitted import surface for route modules.
- One central `unwrap(response)` helper (§5.3) converts responses into `(ok, data_or_error)`.

### 2.3 Authentication — signed session cookie

The backend accepts Bearer JWTs. The frontend stores tokens in FastHTML's server-signed **session** (Starlette SessionMiddleware) and injects them as Bearer headers on in-process calls:

```python
# after successful POST /api/v1/auth/login (TokenResponse):
session["access_token"]  = data["access_token"]
session["refresh_token"] = data["refresh_token"]
session["user"]          = data["user"]          # UserResponse dict
session["csrf"]          = secrets.token_hex(16)
# logout: POST /api/v1/auth/logout (server revokes refresh), then session.clear()
```

- Session cookie: `HTTPSOnly=True`, `SameSite="lax"`.
- `require_login` (mirrors faststrap's `require_auth` preset, `login_url="/login"`) guards all `/app/*` routes; `require_role("school_admin")` guards admin routes.
- **Refresh handling:** on API 401, attempt exactly one `POST /refresh-token` with the stored refresh token; retry the original call once; on failure clear the session and redirect to `/login?expired=1`. Never loop.
- **CSRF:** every state-changing form/HTMX request carries a signed hidden `csrf` field (generated at login), validated by an `app.before` hook on non-GET UI routes. In-process forwarded calls additionally re-derive the user from the JWT, so a stolen cookie alone cannot act.

### 2.4 Project layout

```
skuphase/app/frontend/
├── app.py            # FastHTML instance, add_bootstrap, session middleware, mounts
├── api.py            # in-process API client + unwrap/error mapping
├── deps.py           # require_login, require_role, current_user helpers
├── theme.py          # brand tokens -> create_theme() config
├── components/
│   ├── layout.py     # AppShell (sidebar/topbar), AuthShell, MobileNav
│   ├── feedback.py   # toast helpers, error banner, empty-state helpers
│   ├── exam.py       # ExamCard, SectionBlock, PassageBlock, QuestionPreview
│   └── workflow.py   # StatusBadge mapping, ActionButtons by role+state
└── routes/
    ├── public.py     # landing, about, privacy
    ├── auth.py       # login, register (school/individual), reset, accept-invite
    ├── dashboard.py  # role-aware home
    ├── exams.py      # list, detail, generate wizard, review, approve, export
    ├── proposals.py  # school governance (create/list/generate)
    ├── bank.py       # question bank browse/edit
    ├── users.py      # staff management (admin)
    ├── settings.py   # school profile/settings (admin)
    └── ops.py        # platform stats (admin)
app/assets/css/custom.css   # brand tokens only (§3)
app/assets/img/logo.svg
tests/frontend/             # FastHTML route tests (TestClient)
```

Large pages never become 1,000-line files: page = route function + composition functions in `components/`.

---

## 3. Design System

**Principle: "simple as possible for easy usage."** SkuPhase is a productivity tool for busy teachers, some on low-end Android phones and patchy connections. Dense consumer polish is explicitly out of scope; clarity, big touch targets, and obvious next actions win. This is a **Hybrid** app in faststrap terms: a clean branded shell with functional, low-noise interiors.

### 3.1 Color theme (light mode only)

Adopted from the product's established V0 palette — institutional, calm, trustworthy. **No dark mode** (explicit product decision; avoids half-tested themes).

| Token | Value | Usage |
| --- | --- | --- |
| `--brand-primary` | `#00412E` deep green | navbar/sidebar shell, primary buttons, links |
| `--brand-secondary` | `#96BF8A` sage | secondary accents, active nav highlight, progress |
| `--brand-shell` | `#E8EAE5` light neutral | page background |
| `--brand-surface` | `#FFFFFF` | cards, panels, forms |
| `--brand-accent` | `#10b981` emerald | success states, "approved" |
| `--brand-warning` | `#f59e0b` amber | "under review", pending states |
| `--brand-danger` | `#ef4444` | errors, destructive actions, "failed" |

Semantic workflow-status mapping (single mapping function, used everywhere):

| `workflow_state` | Badge variant |
| --- | --- |
| `generation_requested` | info (spinner badge) |
| `teacher_review` | warning |
| `final_submitted_by_teacher` | secondary |
| `approved` | success |
| `refinement_requested` | warning-outline |
| `status == failed` | danger |

Rules: never use default Bootstrap blue as identity; max one accent color per screen region; status is conveyed by **badge text + color**, never color alone (accessibility).

### 3.2 Typography & spacing

- Font: **Nunito Sans** (fallback system stack) — legible at small sizes on low-DPI phones.
- Page title (`.app-page-title`): `1.25rem`, weight 700. Section titles: `1.05rem`/700. Body: `0.92rem`. Labels/helpers: `0.78rem`, muted.
- Spacing rhythm (reused everywhere): `0.5rem / 0.75rem / 1.5rem / 2.25rem`. Implemented via Bootstrap utilities (`g-3`, `mb-3`, `p-2 p-lg-4`) — **no custom media queries for layout**.
- Radius: controls `0.5rem`, cards `0.75rem`. Shadows: soft single-level (`0 6px 24px rgba(15,23,42,.08)`); no glassmorphism.

### 3.3 Layout shells

Three shells, all in `components/layout.py`:

1. **PublicShell** — `NavbarModern` (logo, "Sign in", "Get started") + content + minimal footer. For landing/about/privacy.
2. **AuthShell** — `AuthLayout`: centered card on `--brand-shell` background, logo top, single-column form. For login/register/reset/invite.
3. **AppShell** — for everything under `/app`:
   - Desktop (≥ md): fixed deep-green **collapsible sidebar** (per `UI_design/Exams.png`: logo top-left, collapse chevron, nav items with icons, active item = darker inset block, role label pinned at sidebar bottom, e.g. "SCHOOL ADMIN") + white top bar (breadcrumb `Home > Exams`, role chip, school chip, notification bell with count, avatar + name + role badge) + content area on `--brand-shell`.
   - Mobile (< md): top bar with hamburger → `Drawer` nav; sticky **`BottomNav`** with the 3 highest-frequency destinations (Dashboard, Exams, Generate).
   - Sidebar visibility by role/account (single `nav_items(user)` function):
     - Everyone: Dashboard, Exams, Question Bank
     - `teacher`/`auditor` (school staff only): Proposals
     - `school_admin`: Proposals, Staff, Settings, Operations
     - `individual_teacher`: NO Proposals/Staff/Settings/Operations items (their workspace is auto-administered)

### 3.4 Faststrap component usage (verified available in 0.8.2)

| UI need | Component |
| --- | --- |
| Forms | `Form`, `FormGroup`, `FormFloatingLabel`/`Input`, `Select`, `SearchableSelect`, `FormErrorSummary`, `FormGroupFromErrors`, `map_formgroup_validation` |
| Submit buttons | `LoadingButton` preset (auto spinner + disable + `aria-busy`) — **mandatory for every mutation** |
| Feedback | `ToastContainer` in AppShell base + `toast_response()` preset in HTMX handlers; `ModernToast` variants |
| Confirm destructive | `ConfirmDialog` / `ConfirmPrompt` preset (`hx_confirm` acceptable for simple cases) |
| Lists/tables | `DataTable` (striped, hover) for exams/users/bank; `Pagination` preset + `InfiniteScroll` only for bank browse |
| Empty states | `EmptyState` with one clear CTA — mandatory on every list page |
| Loading regions | `Spinner`, `PlaceholderCard` for HTMX swap targets; `PollUntil` preset for generation polling |
| Status | `StatusBadge`/`Badge` via §3.1 mapping |
| Multi-step entry | `Stepper`/`FormWizard` for the exam-generation wizard |
| Passages/questions | `Card`, `Markdown` (question text is markdown; the generator validates balanced fences) |
| Catalogue pickers | cascading `Select`s (§6.4); `SearchableSelect` for subject when > 20 options |
| Errors | `ErrorDialog` for HTMX failures; inline `Alert` for page-level |

### 3.5 Reference prototype — `UI_design/` screenshots (VISUAL SOURCE OF TRUTH)

The V0 prototype screenshots in `skuphase/UI_design/` are **the authoritative visual reference**. When building any screen below, open the named screenshot and match its layout, spacing, and component treatment — this spec supplies the *corrections* (dead nav items, stale copy, non-existent data) listed per screen. Verdicts:

| Screenshot(s) | Target screen / milestone | Verdict | Mandatory adjustments when building |
| --- | --- | --- | --- |
| `home.png`, `home2.png` | Landing `/` (M1) | **Adopt** | Keep current copy rules: no "documents/RAG" claims; AI-drafts-from-curriculum messaging only |
| `Register.png`, `Register2.png` | Register `/register` (M2) | **Adopt** | Must map to the two real modes: individual teacher vs school + admin (§6.1/§6.2) |
| `Dashboard.png` | `/app` dashboard (M2/M3) | **Adopt shell + card grid** | Wire stat numbers to real endpoints (§6.8); sidebar items are role-filtered per §3.3 — no Documents/Assets/RAG |
| `Exams.png`, `Exams2.png` (duplicate takes) | Exams list `/app/exams` (M3) | **Adopt nearly as-is** | (1) Remove Documents/Assets/RAG Search nav. (2) Filter pills use real vocabulary: All / Approved / In Review / Generating / Draft / Failed. (3) Quality-score bar renders only for AI-generated exams (manual exams have no quality data). (4) Sample rows must be **Pre-Nursery–Primary 6** subjects — JSS/SSS does not exist in the dataset yet |
| `Exams3.png` | "New Exam" entry modal (M3) | **Adopt directly** | Fix stale copy: "Let AI draft from your documents" → "Let AI draft from the national curriculum". Two cards = the two real paths: Generate with AI → `/app/exams/new`; Blank exam → `/app/exams/new/manual` |
| `Exams4.png` | Exam detail (review) `/app/exams/{id}` (M3) | **Adopt with additions** | Section-summary cards + tab strip (Questions / Preflight / Quality Report / Audit Comments) are required. **Add what the screenshot omits:** workflow action buttons (Refine, Submit Final, Approve — visibility per §3.1 state mapping and §6.6), Delete (confirm dialog). Section cards render from the real `sections` config |
| `Exams5.png` | Exam detail → Quality Report tab (M3) | **Adopt the visual design, NOT the data** | Render **only real validator dimensions** (counts, marks totals, answer keys, format checks, passage grounding — from the quality snapshot). Do NOT invent "Asset integration" or "6/6 Bloom's levels" — those are not computed. Keep the card + horizontal-bar treatment |
| `Exams6.png` | Exam detail, generating state (M3) | **Adopt directly** | The "No questions yet / Generation in progress…" card is the `PollUntil` target — polls `/ui/exams/{id}/poll` until state leaves `generation_requested` |
| `Exams7.png` | Exam detail → Preflight tab, not-run state (M3) | **Adopt directly** | "Run Preflight Check" CTA → real preflight endpoint; result renders pass banner (Exams4) or the failed-check list |
| `Exams8.png` | Exam detail → Quality Report, unavailable state (M3) | **Adopt directly** | — |

**Global rules from the prototype (apply everywhere):**
1. **Never build** the sidebar items Documents, Assets, or RAG Search — those subsystems were deleted from the architecture. The school-admin sidebar is: Dashboard, Exams, Generation Proposals, Question Bank, Users, School Settings, Operations (Users/Settings/Operations land in M5/M6 — render but may link to "coming soon" placeholders until then). Individual-teacher sidebar: Dashboard, Exams, Question Bank only.
2. Breadcrumb topbar pattern (`Home > Exams > {title}`) on every `/app` page.
3. Status filter pills with live counts on every list page.
4. Rounded white cards on the `--brand-shell` background; soft single-level shadows; generous section summary cards with icon + name + counts.
5. All sample/demo copy must reference **Primary 1–6** subjects (dataset reality), never JSS/SSS.
6. The prototype predates manual exam entry — the "Blank exam" card in Exams3 is its entry point; the manual-entry form itself follows §6.4a, styled consistently with the prototype's card/form language.

---

## 4. Backend Contract Summary (the routes the UI consumes)

Complete verified surface (`@router` decorators). All paths prefixed `/api/v1`.

**Auth** (`auth_router.py`): `POST /auth/register` (school + nested `admin_user`), `POST /auth/register-individual`, `POST /auth/login` → `TokenResponse{access_token, refresh_token, expires_in, user}`, `POST /auth/refresh-token`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/accept-invite`, `GET /auth/me` → `CurrentUser{user_id, school_id, role, account_type, full_name, ...}`, `POST /auth/logout`.

**Curriculum** (`curriculum_router.py` — the generation wizard's pickers): `GET /curriculum/classes`, `GET /curriculum/subjects?class_level=`, `GET /curriculum/terms?...`, `GET /curriculum/weeks?...`, `GET /curriculum/search?q=`.

**Exams** (`exams_router.py`):
- Generation: `POST /exams/generate` (async; → `{exam_id, status, poll_endpoint, warnings}`), `POST /exams/manual-submit`, `POST /exams/generation-proposals`, `GET /exams/generation-proposals`, `POST /exams/generation-proposals/{id}/generate` (admin).
- Lifecycle: `GET /exams` (filterable list), `GET /exams/{id}` (full detail: sections, questions, passages, language), `PUT /exams/{id}` (manual edit), `POST /exams/{id}/submit-final` (teacher), `POST /exams/{id}/refine` (LLM feedback), `POST /exams/{id}/refine-from-comments` (LLM from audit comments), `POST /exams/{id}/approve` (admin, runs preflight), `DELETE /exams/{id}`.
- Quality/governance: `GET /exams/{id}/preflight`, `GET /exams/{id}/quality-report`, `GET /exams/{id}/quality-snapshots`, `POST /exams/{id}/audit-comments`, `GET /exams/{id}/audit-comments`.
- Export: `POST /exams/{id}/export` → `{file_name, download_url}`, `GET /exams/{id}/exports/{file_name}` (PDF), `GET /exams/{id}/exports`.
- Bank: `POST /exams/{id}/question-bank/save`, `GET /exams/question-bank/items`, `PATCH /exams/question-bank/items/{id}`.

**Users** (`users_router.py`, admin): `POST /users/invite`, `GET /users`, `GET /users/invites/pending`, `POST /users/invites/{id}/resend`, `PUT /users/{id}/status`, `PUT /users/{id}/role`, `DELETE /users/{id}`.

**Schools** (`schools_router.py`, admin): `GET/PUT /schools/{id}`, `GET/PUT /schools/{id}/settings`.

**Ops** (`ops_router.py`, admin): 2 dashboard stat endpoints.

Key request payload the UI must build — `ExamGenerationRequest`: `subject`, `grade_level`, `term`, `selected_weeks[]`, `sections[]` (`section_number`, `section_title`, `question_type` ∈ multiple_choice/short_answer/essay/true_false, `num_questions`, `marks_per_question`, `instruction_type`, optional `passage{title, body}`, `allow_sub_parts`), `duration_minutes`, `language`, `custom_instructions`, `difficulty_distribution`, `include_diagrams`.

Legal workflow transitions the UI must mirror (from `core/workflow.py`): `teacher_review → final_submitted_by_teacher`; `final_submitted_by_teacher → approved | teacher_review`; `approved` is **terminal** — the UI must never render refine/regenerate buttons on approved exams.

---

## 5. Feedback & Error Handling (the "modern toast" standard)

### 5.1 The three feedback layers (every action, no exceptions)

1. **Immediate (0–300 ms):** no indicator needed, but any mutation still ends in a toast.
2. **In-flight (300 ms–5 s):** `LoadingButton` on the trigger (spinner + disabled + `aria-busy`). For HTMX swaps of large regions, `Spinner`/`PlaceholderCard` inside the target — never a blank flash.
3. **Long-running (> 5 s):** generation polling (§6.5) with a persistent progress card ("Generating your exam… this usually takes 15–40 seconds") — the card is the feedback, not a spinner in a button.

### 5.2 Toast policy (modern, consistent, sparse)

- One `ToastContainer` in the AppShell base layout: top-right on desktop, **top-center full-width** on mobile (thumb-reachable, unmissable).
- All toasts via the `toast_response(content, message=..., variant=..., toast_id="global-toast-container")` preset, so one HTMX response can swap content **and** fire the toast out-of-band.
- Variants: `success` (created/approved/exported/saved), `danger` (API failure), `warning` (partial success: "Generated with 2 warnings — review flagged questions"), `info` (neutral notices).
- Duration: success/info 4 s; warning 7 s; danger **sticky until dismissed** — errors must not auto-vanish.
- Copy style: plain, specific, actionable — "Exam approved and ready to export", never "Operation successful". Never raw exception text (§5.3).
- Toasts confirm **outcomes**; they are not used for form validation — that renders inline (`FormGroup(error=...)`) plus `FormErrorSummary` at the top of the form.

### 5.3 Centralised error mapping (`api.unwrap`)

One function converts every API response into a UI-safe result:

```python
def unwrap(resp) -> tuple[bool, Any]:
    if resp.is_success:
        return True, resp.json()
    detail = None
    try:
        detail = resp.json().get("detail")
    except Exception:
        pass
    if resp.status_code == 422 and isinstance(detail, list):
        return False, {"kind": "validation",
                       "fields": {".".join(map(str, e["loc"][1:])): e["msg"] for e in detail}}
    if resp.status_code == 401: return False, {"kind": "auth", "message": "Your session expired. Please sign in again."}
    if resp.status_code == 403: return False, {"kind": "forbidden", "message": FRIENDLY_403.get(str(detail), "You do not have permission to do that.")}
    if resp.status_code == 404: return False, {"kind": "not_found", "message": "That item no longer exists."}
    if resp.status_code == 429: return False, {"kind": "rate_limited", "message": "Too many attempts. Please wait a few minutes and try again."}
    if isinstance(detail, dict):   # e.g. preflight failure {message, errors, warnings}
        return False, {"kind": "detail", "message": detail.get("message", "Request failed."), "data": detail}
    return False, {"kind": "generic", "message": "Something went wrong. Please try again."}
```

Rules:
- **Never** render raw exception text or stack traces. Backend 500 bodies may contain internals; the UI shows the generic message.
- Structured `detail` dicts (e.g. preflight `{message, passed, errors, warnings}`) render as an `Alert` with an itemised error/warning list, not a flattened string.
- Every HTMX handler that can fail returns either swapped content with an inline `Alert`/`ErrorDialog` **or** an out-of-band danger toast — silence is a bug.
- `422 validation` results map back onto form fields via `FormGroupFromErrors` / `map_formgroup_validation`.

### 5.4 Page-state contract (all four states on every dynamic page)

| State | Implementation |
| --- | --- |
| Loading | `PlaceholderCard` in the HTMX target or server-rendered skeleton on first paint |
| Empty | `EmptyState` with a single CTA (empty exams list → "Generate your first exam") |
| Error | Inline `Alert(variant="danger")` with a Retry button (re-triggers the HTMX fetch) |
| Success | Swapped content + success toast on the triggering action |

---

## 6. User Flows (detailed, step-by-step)

Every flow lists: actor, entry point, steps with the exact API call, feedback, and failure handling.

### 6.1 Registration — Individual Teacher (`/register` → tab "I teach on my own")

**Actor:** unauthenticated visitor. **API:** `POST /auth/register-individual` with `IndividualTeacherRegistrationRequest{full_name, email, password, phone_number?, workspace_name?}`.

1. Visitor clicks **Get started** → `/register` page with a two-tab card: "School" / "Individual teacher" (tabs are links, not JS tabs: `/register` and `/register?mode=individual`).
2. Individual tab shows: Full name*, Email*, Password* (helper text: min 8 chars), Phone (optional), Workspace name (optional; placeholder explains the default "`[Name]'s Workspace`").
3. Password field has live strength helper (client-side length check only; server re-validates).
4. Submit via `LoadingButton` → `POST /auth/register-individual`.
   - **422** → inline field errors + summary (§5.3), form values preserved.
   - **Email already registered (409/400)** → inline error on email: "An account with this email already exists. Try signing in."
   - **Success** → the response contains `user_id`, `school_id` (personal workspace), `user`. UI immediately performs the login step (see below), then redirects to `/app` with success toast: "Welcome to SkuPhase! Your workspace is ready."
5. Auto-login after registration: call `POST /auth/login` with the just-entered credentials; store tokens per §2.3. If auto-login fails (rare), redirect to `/login?registered=1` with info toast.
6. Email verification banner: after login, `GET /auth/me` returns `is_verified`. If false, AppShell shows a dismissible info banner: "Verify your email to receive exam PDFs by mail later. Resend link" → `POST /auth/resend-verification`. **Verification never blocks usage** (product decision).

### 6.2 Registration — School + Admin (`/register?mode=school`)

**API:** `POST /auth/register` with `SchoolRegistrationRequest{school_name, contact_email, contact_phone?, address?, plan_id?, admin_user{...}}`.

1. School tab shows two grouped sections in one card (`FormSection`): "School details" (name*, contact email*, phone, address) and "Administrator account" (full name*, email*, password*).
2. Same submit/validation/feedback behaviour as §6.1. On success → auto-login → `/app` with toast "School registered. You are signed in as administrator."
3. The admin lands on the **admin dashboard** (§6.8) and sees a "Next steps" card: ① Invite teachers (`/app/staff/invite`), ② Review the first proposal or generate directly, ③ Set school profile (`/app/settings`).

### 6.3 Login, logout, password reset, email verification, invite acceptance

**Login (`/login`)** — `POST /auth/login` with `UserLogin{email, password}`:
1. Single card: email*, password* (show/hide toggle), "Forgot password?" link, submit.
2. **Success** → store tokens (§2.3), fetch nothing extra (`user` is in the response), redirect: `individual_teacher` → `/app` (teacher dashboard), `school_admin` → `/app` (admin dashboard), other roles → `/app`.
3. **401 wrong credentials** → inline Alert over the form: "Incorrect email or password." (never "user not found" — no account enumeration).
4. **429 rate-limited** → inline Alert: "Too many attempts. Please wait a few minutes and try again." (button stays disabled for 60 s with a countdown).
5. `?expired=1` query → info toast "Your session expired — please sign in again." `?registered=1` → info toast "Account created — sign in below."
6. **Logout** (AppShell profile dropdown): confirm not required; calls `POST /auth/logout` (server revokes the refresh token — real revocation since the token-generation fix), clears session, redirects to `/login`, toast "Signed out."

**Forgot/Reset password (`/forgot-password`, `/reset-password?token=…`)**:
1. Forgot form: email* → `POST /auth/forgot-password`. **Always** shows the same success toast regardless of whether the account exists (no enumeration): "If that email is registered, a reset link is on its way."
2. Reset form (from email link): new password* + confirm* → `POST /auth/reset-password` `{token, new_password}`. Success → redirect `/login`, toast "Password updated — sign in with your new password." Invalid/expired token (4xx) → inline danger Alert with "Request a new link" action.

**Accept invitation (`/accept-invite?token=…`)** (invited school staff):
1. Card shows inviter/school context if available + fields: password*, full name (pre-filled if provided in invite) → `POST /auth/accept-invite` `{token, password, full_name?}`.
2. Success → auto-login → `/app`, toast "Welcome to {school}! You're all set."
3. Expired/used token → dedicated error page state with "Ask your administrator to resend the invite" and a link to `/login`.

### 6.4 Exam Generation — Individual Teacher (the flagship flow, `/app/exams/new`)

**Actor:** `individual_teacher` (or `school_admin` generating directly). **APIs:** curriculum endpoints + `POST /exams/generate`.

**Entry:** "Generate exam" primary button (dashboard quick action, exams list, bottom-nav center button on mobile).

**Step 1 — What (Stepper step 1 of 3: "Curriculum")**
1. Class picker: `GET /curriculum/classes` → `Select` (server-rendered on page load; values like "Primary 1…Primary 6", ordered by `level_order`).
2. Subject picker: `Select` with `hx_get=/ui/partial/subjects?class_level=…` on change → `GET /curriculum/subjects?class_level=` swaps the options (HTMX partial; `LoadingButton`-equivalent spinner inside the select's container). SearchableSelect if > 20 options.
3. Term picker: same pattern → `GET /curriculum/terms`.
4. Weeks picker: multi-select chips → `GET /curriculum/weeks?...` shows weeks with their topics; teacher toggles any subset (default: all shown). Chips are checkboxes — no exotic JS.
5. If the chosen subject/term has no scheme data (backend generates warnings downstream), show a passive hint: "No official scheme data for this selection yet — the exam will follow standard national curriculum objectives." (Non-blocking; matches backend behaviour of warning, not failing.)

**Step 2 — Structure (Stepper step 2: "Sections")**
1. Section builder (1–5 sections): each section is a `Card` with: title (pre-filled "SECTION A: OBJECTIVES"), question type (`Select`: multiple_choice / short_answer / essay / **true_false**), number of questions (number input 1–100), marks per question, instruction type (answer_all / answer_any_n → reveals answer_count / compulsory_plus_optional → reveals compulsory question numbers), optional "add comprehension passage" toggle → reveals `PassageSpec` title + body `Textarea` (helper: "Paste or write the reading passage; every question in this section will be answerable from it"), and for short_answer/essay an `allow_sub_parts` `Switch` ("Split into (a)/(b) sub-parts").
2. "Add section" (≤ 5) and remove-section buttons; totals bar live-computed server-side on each HTMX change (target `#totals-bar`): "Total: 40 questions · 100 marks · 120 minutes".
3. Duration input (default 120), Language `Select` (English/Igbo/Yoruba/Hausa — helper: "Questions and answers will be written in this language").

**Step 3 — Polish (Stepper step 3: "Options")**
1. Difficulty distribution (optional): three range inputs or preset chips (e.g. "Balanced" = 40/40/20, "Challenge" = 20/50/30) → `difficulty_distribution`.
2. Custom instructions `Textarea` (≤ 1000 chars, counter shown; helper: "Anything specific — e.g. 'focus on fractions', 'use my pupils' names'").
3. Include diagrams `Switch` (default off).
4. Review summary card (all chosen values, read-only) + **Generate** `LoadingButton`.

**Submit:** UI assembles `ExamGenerationRequest` (server-side handler function builds it from form fields — the form never posts raw JSON) → `POST /exams/generate`.
- **429/403 budget** (10/day cap or LLM budget) → danger Alert with the message from the API + "Try again tomorrow" guidance for the daily cap.
- **422** → jump the stepper back to the offending step with inline errors.
- **Success** → redirect to `/app/exams/{exam_id}` which is in `generation_requested` state → **polling view** (§6.5). `warnings` in the response (curriculum coverage notices) are surfaced on the exam page as a warning Alert.

### 6.4a Manual exam entry — no AI (`/app/exams/new?mode=manual`)

**Actor:** any teacher/admin. **API:** `POST /exams/manual-submit` with `ManualExamSubmissionRequest{subject, grade_level, duration_minutes?, instructions?, language, questions[]}`. **No LLM call, no daily-budget consumption.**

**Entry:** from the same "Generate exam" entry point, a two-option choice card ("Create with AI" / "Type it myself") — or directly from dashboard quick action "New exam (manual)".

1. **Exam details card:** subject*, class* (`Select` fed by `GET /curriculum/classes` — reuses the wizard's partial), duration, general instructions, language `Select` (default English).
2. **Question repeater:** "Add question" appends one question card to the form: number (auto-incremented, editable), type (`Select`: multiple_choice / short_answer / essay / true_false), question text* (`Textarea`), marks*, and type-conditional fields (options A–E + correct answer for MCQ/true_false; marking scheme points for short_answer/essay; optional topic/difficulty). Each card has a remove button and move up/down arrows (HTMX partial swap, server-maintained ordering).
3. **Feedback:** running total bar ("12 questions · 60 marks") re-computed server-side on every add/remove/change; per-field inline validation; `FormErrorSummary` on submit.
4. **Submit** (`LoadingButton`) → `POST /exams/manual-submit`. **Success** → redirect to `/app/exams/{id}`: manual exams are created directly in `final_submitted_by_teacher` (individual teachers approve their own; school staff continue through §6.6 exactly like AI exams) → toast "Exam created — ready for review/export."
5. **Failure:** 422 field errors map via `unwrap` onto the question cards (errors are per-question-indexed). **Nothing is lost on failure** — the form re-renders with all entered values preserved.
6. **Scope fence (v1):** one-question-at-a-time form only. Bulk paste from Word, CSV/DOCX import, and composing from bank items are deferred to the M7+ backlog (§9.4) — they are where effort would balloon.

*Why this is in M3, not deferred:* the endpoint already exists and is tested; the review/approve/export UI it flows into is built in M3 anyway; and it serves the founding use case (a teacher with existing questions needs nothing from the AI).

### 6.5 Generation polling view (`/app/exams/{id}` in `generation_requested`)

1. Page renders a full-width progress card: sage progress bar (indeterminate pulse), status line "Generating your exam…", sub-line "Usually 15–40 seconds. You can leave this page — your exam will be here."
2. A `PollUntil` preset targets `#exam-body` with `hx_get=/ui/exams/{id}/body` every **3 s**, terminating when the returned fragment sets `hx-swap-oob` "done" (server decides: `workflow_state == teacher_review` or `status == failed`).
3. **Success** → fragment swaps to the full exam review view (§6.6) + success toast "Exam ready for your review." Any curriculum warnings render as a warning Alert above the questions.
4. **Failure** (`status == failed`) → danger Alert card: "Generation failed. You have not lost your daily allowance." + "Try again" button (re-POSTs `/exams/generate` with the same payload, stored in `session["last_generation_request"][exam_id]` for convenience) + "Contact support" link.
### 6.6 Exam review & refinement (`/app/exams/{id}` in `teacher_review`)

**Actor:** owner (teacher/individual) or any school-staff role per backend permissions. This is the highest-value screen — it must feel like proofreading a paper, not operating software.

**Layout:**
1. **Header card:** subject, class, term/weeks, total marks, duration, language, `StatusBadge`. Primary action depends on state/role via a single `ActionButtons(exam, user)` component (never ad-hoc buttons): `teacher_review` → "Submit for approval" (individual) / "Submit final draft" (school staff) primary; "Refine with AI", "Edit manually", "Export", "Delete" secondary/danger (delete + refine behind `ConfirmDialog`).
2. **Quality panel (collapsible):** `GET /exams/{id}/quality-report` → traffic-light badge, coverage score, distribution table, quality flags. "Run checks" button → `GET /exams/{id}/preflight` → `{passed, errors, warnings}` as an itemised Alert; the UI pre-warns because submit-final/approve are blocked server-side when preflight fails.
3. **Question list, section by section:** section title card → (if present) `PassageBlock` rendered **once** (bordered card: title + body) → each question row: number, `Markdown`-rendered text, options (A–E) or marking scheme/sub-parts, marks, difficulty chip. Answers hidden behind a per-exam "Show answers" toggle (default hidden).
4. **Per-question actions:** "Comment" (`POST /exams/{id}/audit-comments`, feeds the refine-from-comments flow) and "Edit inline" (`InlineEditor` row-swap; save via `PUT /exams/{id}` — no LLM call, instant).

**Refine with AI (`POST /exams/{id}/refine`):**
1. Opens a `Modal`: feedback `Textarea` ("Make question 3 easier; add one more on fractions"), optional question-number multi-select (empty = whole exam), and an explicit budget note: "Uses 1 of your 3 AI refinements for this exam."
2. `LoadingButton` submit. On success the question list re-fetches + toast "Exam refined." Budget exhaustion (403/429) → danger toast with the API message + "edit manually instead" guidance.

**Refine from comments (`POST /exams/{id}/refine-from-comments`):** button visible when audit comments exist, with count badge ("Apply 4 comments with AI"). Same modal/budget note. Comments render under each question with author + timestamp.

**Submit final (`POST /exams/{id}/submit-final`)** (school staff only): confirm dialog → toast "Submitted for approval." Individual teachers never see this button — their path is approve directly.

**Approve (`POST /exams/{id}/approve`)** (admin / individual teacher):
1. Visible in `final_submitted_by_teacher` (school) or `teacher_review` (individual).
2. Click → first `GET /exams/{id}/preflight`. If not passed → render the preflight Alert; do **not** call approve.
3. If passed → `ConfirmDialog` ("Approved exams are locked for editing.") → `POST /exams/{id}/approve` → toast "Exam approved — ready to export", badge success, page re-renders read-only with export CTA and **no refine/regenerate/edit buttons** (approved is terminal).

**Export (`POST /exams/{id}/export`):**
1. Available from review states and prominent when approved. Modal: "Include answer key?" switch → Export.
2. `LoadingButton` → success returns `{file_name, download_url}` → trigger download of `download_url` immediately + toast "PDF ready — downloading."
3. Preflight-gated refusal (400 with structured detail) renders the itemised failure Alert (§5.3 `kind=detail`).
4. "Previous exports" (`GET /exams/{id}/exports`) lists earlier PDFs for re-download.

**Delete exam (`DELETE /exams/{id}`):** danger zone, `ConfirmDialog` with explicit copy ("Permanently deletes the exam and all its questions.") → redirect + toast.

### 6.7 School governance flow (proposals)

**Actors:** `teacher`/`auditor` propose; `school_admin` generates. **APIs:** `POST /exams/generation-proposals`, `GET /exams/generation-proposals`, `POST /exams/generation-proposals/{id}/generate`.

1. **Create proposal (`/app/proposals/new`):** the same three-step wizard as §6.4 plus "What should this exam achieve?" free-text (`desired_outcomes`) — final button is **"Submit proposal"**, not Generate. Success toast: "Proposal sent to your administrator."
2. **Admin dashboard** shows a pending-proposals card; proposal detail renders all wizard choices read-only + "Generate exam" primary button with budget confirm ("Uses 1 of your 10 exams today").
3. Generation from a proposal → inline polling (§6.5 pattern) on the proposal page, then the exam link activates. Proposal status flips `open → used` (backend-driven).
### 6.8 Dashboard (`/app`) — role-aware

**Individual teacher:** StatCards row (Total exams / Awaiting review / Approved this term / Daily generations left = 10 − used), primary "Generate exam" CTA, recent exams `DataTable` (subject, class, status badge, updated, actions).
**School admin:** StatCards (Generating / Under review / Awaiting approval / Approved), pending-proposals list (count + top 5), recent exams table, quick actions (Generate, Invite staff, Review proposals).
**Teacher (school staff):** my exams, my proposals, exams awaiting my final submit. **Auditor:** exams open for review, my comments.
The "generating" count card embeds a 10 s `AutoRefresh` partial so in-flight generations appear without manual reload.

### 6.9 Secondary flows (compact spec)

- **Exams list (`/app/exams`):** filter chips (status/class/subject) + `ActiveSearch` (debounce 300 ms → server partial); `DataTable` on desktop, card list on mobile; `Pagination`. Empty-state CTA → wizard.
- **Question bank (`/app/bank`):** filters (subject/class/topic/review_status) + `ActiveSearch` on question text; expandable rows; "Save to bank" from exam detail (`POST /exams/{id}/question-bank/save` — all or selected questions); inline edit via `InlineEditor` (`PATCH /exams/question-bank/items/{id}`); `review_status=pending` filter lets testers see items awaiting platform promotion.
- **Staff management (`/app/staff`, admin):** invite form (email + role select teacher/auditor → `POST /users/invite`); users table with activate/deactivate, change role, remove (each `ConfirmDialog`); pending invites with resend; toasts note "They'll receive an email invite."
- **School settings (`/app/settings`, admin):** profile (`PUT /schools/{id}`) + settings (`PUT /schools/{id}/settings`) — render **only** fields the current schema accepts (nothing LLM-provider related; that was removed).
- **Operations (`/app/ops`, admin):** the two ops endpoints as StatCards with 10 s `AutoRefresh`; no charts in v1.

### 6.10 Public pages

- **Landing (`/`)**: `Hero` ("Curriculum-aligned exams in seconds — built for Nigerian primary schools"), how-it-works (3 steps), feature grid (official NERDC scheme objectives, past-question grounding, deterministic quality checks, review workflow), pricing teaser, FAQ, footer. CTAs → `/register`.
- **About**, **Privacy/Terms** placeholders, branded **404/500** pages with recovery links.
- Trust copy must be honest: data coverage is Pre-Nursery–Primary 6; every exam passes a human review step; British-English, Nigerian-context generation.

---

## 7. Route Map (UI)

| Path | Shell | Access | Purpose |
| --- | --- | --- | --- |
| `/` | Public | all | Landing |
| `/about`, `/privacy` | Public | all | Static pages |
| `/register`, `/register?mode=individual` | Auth | all | Dual-mode registration |
| `/login`, `/forgot-password`, `/reset-password` | Auth | all | Auth |
| `/accept-invite`, `/verify-email` | Auth | token holders | Token flows |
| `/app` | App | logged in | Role-aware dashboard |
| `/app/exams`, `/app/exams/new`, `/app/exams/new?mode=manual`, `/app/exams/{id}` | App | logged in | Exam list / AI wizard / manual entry / detail |
| `/app/proposals`, `/app/proposals/new`, `/app/proposals/{id}` | App | school staff | Governance |
| `/app/bank` | App | logged in | Question bank |
| `/app/staff` | App | school_admin | Staff & invites |
| `/app/settings` | App | school_admin | School profile/settings |
| `/app/ops` | App | school_admin | Platform stats |
| `/ui/partial/*` | — | logged in | HTMX partial endpoints (subjects, weeks, exam body, lists) — internal only |

---

## 8. Responsiveness, Accessibility, Security

**Responsive (mobile-first, mandatory):**
- One-column base layout always; `Row/Col(cols=12, cols_md=…, cols_lg=…)` for expansion. No custom media queries for layout.
- AppShell: sidebar `d-none d-md-block`; `Drawer` via hamburger + sticky `BottomNav` (Dashboard / Exams / Generate) on mobile.
- Touch targets ≥ 44 px; forms single-column on mobile; the generation wizard renders one step per screen.
- Tables become stacked cards on mobile (explicit card-list partial per list page).

**Accessibility baseline:**
- Semantic heading order per page; `FormGroup` labels on every control; `aria-label` on icon-only buttons.
- Status conveyed by text + colour (never colour alone); `LiveRegion` for toast announcements; visible focus states; `SkipLink` in AppShell; `FocusTrap` in modals.
- Contrast: deep green `#00412E` on white passes WCAG AA; sage `#96BF8A` is large-text-only — use a darkened sage for small text.

**Security on the frontend:**
- Session cookie: signed, `HTTPSOnly`, `SameSite=lax`. Tokens never rendered into the DOM or JS globals.
- Signed CSRF hidden field on all mutating UI forms (§2.3).
- All user/LLM text rendered through FastHTML's default escaping; the `Markdown` component only on generated question text (fence balance validated server-side).
- No secrets in `assets/` (there is essentially no custom JS).
- Error pages never reflect URLs/tokens back into HTML (no reflected injection).

---

## 9. Build Order, Quality Gates, Non-Goals

### 9.1 Build order (each milestone demo-able)

1. **M1 — Skeleton:** `frontend/app.py` (FastHTML + `add_bootstrap` once + session middleware), theme tokens, Public/Auth/App shells, mount into `app/main.py`, landing page, first route test. *Exit: app boots, shells render, tests green.*
2. **M2 — Auth:** dual-mode registration, login/logout, session plumbing, `require_login`, toast + `unwrap` error mapping, forgot/reset/verify/accept-invite. *Exit: full auth loop against the real API.*
3. **M3 — Core creation loop (the flagship):** dashboard, exams list, generation wizard (3 steps + curriculum partials), **manual exam entry (§6.4a — simple question repeater)**, polling view, review page (sections/passages/questions rendering), inline edit, submit-final, approve, export + download. *Exit: an individual teacher can both create-with-AI and type-an-existing-exam, then review → approve → export end-to-end.*
4. **M4 — Quality & refinement:** refine modal (with budget note), refine-from-comments, audit comments, quality-report + preflight panels.
5. **M5 — Governance:** proposals (create/list/detail/generate), admin dashboard additions.
6. **M6 — Admin & bank:** staff management, settings, ops page, question bank browse/save/edit.
7. **M7 — Polish:** mobile pass (BottomNav/Drawer), loading/empty/error sweep per §5.4, a11y audit, 404/500 pages, landing copy.

> **Screenshots first:** for M3–M6, `UI_design/` screenshots (§3.5) are the visual source of truth — open the mapped screenshot before building each screen and apply the listed adjustments.

### 9.2 Quality gates (check on every PR)

- Every mutation uses `LoadingButton` and ends in a toast; every form shows inline validation via `FormGroup`/`FormErrorSummary`.
- Every list page implements all four §5.4 states.
- No route module imports SQLAlchemy models or services directly — only `api.py`.
- `add_bootstrap` called exactly once; app assets only under `/assets`; no `/static` collisions.
- Buttons render only for legal workflow transitions (§4/§6.6); approved exams are fully read-only.
- Each new page manually verified at 390 px viewport.
- `tests/frontend/` covers: auth loop, wizard payload assembly, `unwrap` mapping, workflow-state button logic.

### 9.3 Explicit non-goals (do NOT build)

- Document upload, RAG search, or asset pages — the subsystem was deleted from the backend.
- Dark mode, theme toggles, marketing animation (Fx/GSAP), glassmorphism.
- React/Vue/Alpine or any SPA framework; no client-side router.
- Billing/plan UI (`plans` table is unwired — revisit at monetisation).
- Curriculum-mapping UI (`curriculum_mappings` deferred post-pilot).
- One-shot multi-subject "class pack" generation (per-subject exams only — see engineering analysis).
- SSE/WebSockets — 3 s polling is fully sufficient for a 15–40 s job.

### 9.4 Backlog & open items for the product owner

**Backlog (explicitly deferred, do not pull into M1–M6):**
1. Bulk exam import — paste-from-Word / CSV / DOCX for the manual path (§6.4a scope fence).
2. Compose-new-exam from question-bank items (bank → new exam assembly).

**Decisions needed:**
1. Logo/brand asset (spec assumes a placeholder `assets/img/logo.svg`).
2. Landing pricing copy (teaser only until monetisation is modelled).
3. Support contact channel (target of "Contact support" links in failure states).
4. Production domain on FastAPI Cloud (trivialises CORS via same-origin; verify `HTTPSOnly` session cookie end-to-end).



