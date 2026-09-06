# Audit Findings — Implementation Plan

**Source:** `AUDIT_REPORT.md` (2026-09-04 deep audit)
**Status:** Approved plan — work not yet started
**Baseline:** 151/151 tests passing (`..\.venv\Scripts\python.exe -m pytest tests/ -q` from `skuphase/`)
**Rule of engagement:** every phase ends green — run the full suite before moving on. One phase = one PR-sized changeset.

---

## Corrections & Additions to the Audit (found while planning)

Planning-level verification sharpened three findings:

1. **Settings tab count**: the live prototype has **5 tabs** — School Profile, My Account, **Notifications**, **API & Integrations**, Security. The implementation has 4 (Profile, Account, Academic Policy, Security). So the true gaps are **Notifications** and **API & Integrations**; the implementation's extra *Academic Policy* tab is a **justified divergence** (it maps to real `PUT /schools/{id}/settings` backend: active_term, academic_year, min_pass_mark).
2. **More `Flash()`-in-HTMX bugs** than the audit's headline finding — full inventory below (6 sites, not 1).
3. **`exams.py:347` reclassified**: it is inside the *full-page* exams list render (`body_content = Div(Alert(...))`), which is the correct full-page pattern. **Keep as-is.** Similarly, the preflight/quality tab result `Alert`s (653, 678, 1069, 1077) are **persistent tab content**, not ephemeral feedback — **keep as-is, document as exceptions**.

---

## Phase 1 — Feedback Contract Fixes (HIGH) · ~0.5–1 day

**Goal:** every HTMX partial response uses `show_toast()`; `Flash` appears only in full-page redirect flows. This restores the non-negotiable rule from `FRONTEND_SPEC.md §5`.

### 1.1 Convert `return Flash(...)` → `show_toast(...)` in HTMX handlers (6 sites)

All sites verified by `Select-String 'return Flash\('`:

| File:Line | Handler | Current (bug) | Change |
|---|---|---|---|
| `exams.py:1776` | `GET /ui/exams/{id}/poll` | `return Flash(exam.get("message", "Could not load exam."), "danger")` | `return show_toast(...)` |
| `exams.py:1826` | `POST /ui/exams/{id}/submit-final` | `return Flash(data.get("message", "Submission failed."), "danger")` | `return show_toast(...)` |
| `exams.py:1882` | `POST /ui/exams/{id}/export` | `return Flash(data.get("message", "Export failed."), "danger")` | `return show_toast(...)` |
| `exams.py:1903` | `DELETE /ui/exams/{id}` | `return Flash(data.get("message", "Delete failed."), "danger")` | `return show_toast(...)` |
| `ops.py:24` | `_ops_content` (shared by `GET /ui/ops/panel` HTMX partial) | `return Flash("Access restricted to school administrators.", "danger")` | Split the guard: partial handler (`ops.py:160–167`) checks role **before** calling `_ops_content` and returns `show_toast("Access restricted to school administrators.", "danger")`; the full-page path keeps the `Flash` (correct for full pages). |

Import `show_toast` where missing: `exams.py` already imports it (used at approve handler ~line 1866); `ops.py` needs `show_toast` added to the `feedback` import at line 14.

**Note on `exam_delete` success path (`exams.py:1905–1907`)**: success uses `set_flash` + 303 redirect — that is correct and stays.

### 1.2 Convert ephemeral `Alert(...)` → `show_toast(...)` in HTMX responses (4 sites)

| File:Line | Handler | Change |
|---|---|---|
| `exams.py:624` | `tab_questions` error | `return show_toast(exam.get("message", "Could not load questions."), "danger")` |
| `exams.py:650` | `tab_preflight` run error | `return show_toast(data.get("message", "Preflight could not run."), "danger")` |
| `exams.py:1886` | `exam_export` success in `#export-result` | Replace `Alert("Export ready.", ...)` with `show_toast("Export ready.", "success")`; keep the download `A(...)` block and `id="export-result"` |
| `exams.py:1911` | `_wizard_error()` | Replace `Alert(message, variant="danger")` with `show_toast(message, "danger")`; keep the "Back to Step 1" link and `id="wizard-panel"` |

### 1.3 Keep-as-is (documented exceptions — add comments, don't change code)

- `exams.py:347` — full-page list render error banner. Add comment: `# Full-page flow: inline Alert is correct here (FRONTEND_SPEC §5).`
- `exams.py:653, 678` — preflight result summaries (persistent tab state).
- `exams.py:1069, 1077` — quality report content (persistent tab state).
- `exams.py:1088` — comments tab error inside re-rendered tab body (persistent context next to the comment form). Keep; add the same comment.

### 1.4 Update `QUICK_REFERENCE.md`

Add one line under the feedback rules: *"Persistent tab content (preflight/quality results, tab error context) may use inline `Alert`; everything else in an HTMX response is `show_toast`."*

### 1.5 Tests (extend `tests/test_audit_remediation.py`)

- For each converted handler: assert response body does **not** contain the `Flash` wrapper signature and does contain `data-fs-modern-toast` (or the ModernToast marker used by Faststrap).
- Assert `exam_delete` failure still does not set session flash (no `session["flash"]` after failed DELETE).
- Assert ops partial for a teacher role returns toast, ops full page for teacher redirects or renders Flash (unchanged behavior).
- **Existing tests may assert current behavior** — grep `tests/` for `Delete failed` / `Export failed` / `Submission failed` and update expectations.

**Acceptance:** `grep "return Flash\(" app/frontend/routes/*.py` → only full-page handlers remain; full suite green.

---

## Phase 2 — Settings Parity: Notifications Tab + API & Integrations Decision · ~1–2 days

**Goal:** close the fidelity gap at `settings.py:69–72` (4 tabs vs prototype's 5).

### 2.1 Add "Notifications" tab (implement — real user value)

**Prototype content** (verified on live prototype `Settings → Notifications`): 6 toggle rows + "Save Preferences":

| Toggle | Default (prototype) |
|---|---|
| Exam generation completed | ON |
| New audit comments | ON |
| Proposal status changes | ON |
| Document processing done | OFF |
| User joins school | OFF |
| Preflight check failed | ON |

**Backend prerequisite (check first):** inspect `app/api/v1/` for an existing user-preferences endpoint. If none exists, add:
- `GET /auth/me/preferences` and `PUT /auth/me/preferences` in `auth_router.py`, storing a `notification_prefs` JSON dict on the user record (6 boolean keys, defaults above). Schema: `NotificationPrefs` in `app/schemas/auth.py`.

**Frontend (`settings.py`):**
- Add `_tab_link("notifications", "Notifications", "bell")` after "account" (line ~70).
- New tab body: `Form` → 6 `FormCheck`/switch rows (title + muted description, matching prototype copy) → `Button("Save Preferences", type="submit", variant="success", cls="btn-brand rounded-pill px-4")` → `action="/app/settings?tab=notifications"`.
- New handler branch in `update_settings_submit` (line ~223): `target_tab == "notifications"` → collect 6 checkbox keys (unchecked = absent from form → `False`), `PUT /auth/me/preferences`, flash + redirect back to `?tab=notifications`.
- Gate: individual teachers and school admins both see it; school staff teachers see it too (it's a *user* preference, not school config).

### 2.2 "API & Integrations" tab (stub or descope — decide before coding)

The prototype tab shows API-key rotation + Google Drive/WAEC-NECO integrations. **No backend exists for any of it.**

**Recommended:** ship a stub tab now:
- `_tab_link("integrations", "API & Integrations", "plug")`.
- Body: `EmptyState(title="API access is coming soon", message="School API keys and integrations (Google Drive, WAEC/NECO standards) are on our roadmap. Contact your SkuPhase representative to join the pilot.", primary_cta=A("Contact Support", href="/about", ...))`.
- Add descope note to `FRONTEND_SPEC.md §6.12`.

**Alternative (defer):** don't add the tab; document descope in spec only. Cost: 0. Choose at kickoff.

### 2.3 Tests

- `tests/test_frontend_admin.py`: settings page renders 5 (or 6) tab links; notifications tab renders 6 switches; POST `?tab=notifications` persists prefs (mock API) and redirects with success flash.

**Acceptance:** `/app/settings` tab rail matches prototype (Profile, Account, Notifications, [Integrations], Policy, Security); saving toggles persists across reload.

---

## Phase 3 — Onboarding & Rural Usability · ~1 day

**Goal:** close Dimension 3 gaps — the ≤ 15-interaction promise and first-run comprehension.

### 3.1 First-run CTA card on dashboard (`dashboard.py:218–228`)

Insert a curriculum-first hero card between the header and `metrics_row`, shown when `len(exams_all) == 0` (first-run) — or always, as a slim banner, for returning users:

```python
curriculum_cta = Card(
    Div(
        Div(Icon("journal-text", cls="bi fs-4"), cls="app-row-icon brand me-3"),
        Div(
            Strong("Start from the curriculum", cls="d-block"),
            P("Pick a class, subject and week from the NERDC scheme — we pre-fill the exam for you.", cls="text-muted small mb-0"),
        ),
        A(Icon("arrow-right-circle", cls="bi me-1"), "Open Curriculum Explorer",
          href="/app/curriculum", cls="btn btn-brand rounded-pill px-4 flex-shrink-0"),
        cls="d-flex flex-wrap align-items-center gap-3 p-3",
    ),
    cls="border-0 shadow-sm rounded-4 mb-4 bg-white",
)
```

### 3.2 Wizard auto-title (`exams.py` Step 1 form, ~line 1540–1560)

When `class_level`, `subject`, `term` query params are present, prefill the title input:
`f"{class_level} {subject} — {term} Examination"` (append `(Week {weeks})` when `weeks` present). Keep it editable. One-line change in the `Input(..., value=...)` construction.

### 3.3 Polling time expectation (`exams.py:1781–1784`)

Replace `P("Still generating...", ...)` with:
`P("Still generating — this usually takes under 2 minutes. You can keep this tab open.", ...)`.
Wrap the poll fragment container with `**{"aria-live": "polite"}` so status changes are announced (also fixes audit fix-list #12).

### 3.4 UNDER_REVIEW helper copy for teachers (`exams.py` detail action bar)

In `_render_exam_detail(...)` (or the action-button builder), when the exam state is `teacher_review`/`final_submitted_by_teacher` **and** the viewer is a `teacher` (not admin/individual), render below the status badge:
`P("Your exam is with your school admin for approval. You'll get a notification when it's reviewed.", cls="text-muted small mt-2")`.

### 3.5 Proposals explainer for first-time school users (`proposals.py` list route ~line 227+)

When the school has zero proposals, render an `EmptyState` that *explains the workflow*:
title "How proposals work", message "Teachers describe the exam they need. A school admin reviews the request and generates the exam. Everyone can then refine, preflight and export it." + CTA "New Proposal" (existing `/app/proposals/new`). No stateful "seen before" tracking needed — zero-proposal is a good-enough first-run signal.

### 3.6 Tests

- Dashboard with empty exams renders the CTA card (assert `Open Curriculum Explorer` present); with exams, assert absent.
- Wizard GET with `?class_level=Primary 3&subject=Mathematics&term=First Term&weeks=1` → title input `value` contains `Primary 3 Mathematics — First Term`.
- Poll fragment contains `usually takes under 2 minutes` and `aria-live`.
- Proposals empty state contains `How proposals work`.

**Acceptance:** all new assertions green; manual smoke of the Primary-3 journey still ≤ 15 interactions (now ~12 with auto-title).

---

## Phase 4 — Accessibility, Mobile & Print Polish · ~0.5–1 day

### 4.1 Filter pills ARIA (`exams.py:_pill`, ~line 387–398)

The pills are `A` (links), so add **`aria-current`** on the active one:
```python
return A(f"{label}{count_str}", href=href, cls=cls, style=style,
         **({"aria-current": "true"} if is_active else {}))
```
Do the same for curriculum class/subject/term pill links (`curriculum.py:167,182,197`) and settings tab links (`settings.py:61–66`).

### 4.2 Toggle-style buttons get `aria-pressed` (Bloom's pills, show/hide answers)

In `components/exam.py` (question card pill buttons) and the answers toggle, add `aria-pressed="true|false"` matching state. (Buttons, unlike links, use `aria-pressed`.)

### 4.3 Toast container vs bottom nav overlap (`custom.css`)

Append to the mobile media query block:
```css
@media (max-width: 991.98px) {
  #app-toast-container { bottom: calc(4.5rem + env(safe-area-inset-bottom)) !important; }
}
```
(ToastContainer is `bottom-end`; bottom nav is ~4.5rem tall.)

### 4.4 Filter pill tap targets on small screens (`custom.css`)

In the same mobile block:
```css
@media (max-width: 575.98px) {
  .app-table-container + .d-flex .badge.rounded-pill,
  .badge.rounded-pill.px-3 { padding-top: .5rem !important; padding-bottom: .5rem !important; font-size: .95rem !important; }
}
```
(Or add `py-2` classes directly in `_pill` — prefer CSS so the change is one-file.)

### 4.5 Print: prevent question splitting (`custom.css` near line 828)

```css
@media print {
  .app-card, .print-avoid-break { page-break-inside: avoid; }
}
```
Then add `cls="print-avoid-break"` to each question card in `components/exam.py::_question_card` (or rely on `.app-card` if question cards already carry that class — verify first).

### 4.6 Proposal header title clamp (`proposals.py:174`)

`Strong(f"{grade} {subject}", cls="fs-6 text-dark me-2 text-truncate", style="max-width: 22rem;")` — or a 2-line clamp utility in `custom.css` (`.clamp-2 { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }`) if full titles matter.

### 4.7 `hx-indicator` on small partials

- Comments form (`exams.py` `hx_post="/ui/exams/{exam_id}/comments"` construction ~line 2006 region / comments tab): add `hx_indicator="#tab-content-spinner"` and a sibling `Span(..., cls="htmx-indicator spinner-border spinner-border-sm text-muted")`.
- Exports history tab trigger: same pattern.
- Manual-submit form (`hx_post="/ui/exams/manual-submit"`, line 2006): verify it has an indicator; add if missing.

### 4.8 Action-oriented fallback error copy (user-visible strings only)

| File:Line | Current | New |
|---|---|---|
| `exams.py:1903` | `"Delete failed."` | `"We couldn't delete this exam — check your connection and try again."` |
| `exams.py:1882` | `"Export failed."` | `"We couldn't prepare the export — try again in a moment."` |
| `exams.py:1826` | `"Submission failed."` | `"We couldn't submit your exam — check your connection and try again."` |
| `exams.py:347` | `"Could not load exams."` | `"We couldn't load your exams right now — refresh to try again."` |

Backend `message` still takes precedence (`.get("message", <new fallback>)`).

### 4.9 Contrast check (manual, no code until verified)

Run a contrast check on `text-muted` (#6c757d) over the brand-tinted card backgrounds in `custom.css` (`--brand-tint` cards). If any pairing is < 4.5:1, darken the muted color used on those cards only. Record the result in this file's completion log.

### 4.10 Tests

- `_pill` active link carries `aria-current="true"` (exams + curriculum).
- Poll/`aria-live` already covered in Phase 3.
- CSS changes: no unit tests; verify by manual viewport resize + print preview smoke test.

**Acceptance:** keyboard-only pass over exams list + exam detail announces active filter; toasts visibly clear of bottom nav at 375×667; print preview of an exam shows no split questions.

---

## Phase 5 — Regression Tests, Docs & Verification · ~0.5 day

### 5.1 New/updated regression tests (`tests/test_audit_remediation.py` append)

1. `test_htmx_handlers_never_return_flash` — for each of the 5 former `Flash()`-in-HTMX sites (poll, submit-final, export, delete, ops panel guard), mock API failure / non-admin role and assert response does **not** contain the `Flash` wrapper signature.
2. `test_htmx_error_partials_use_toast` — same failure paths assert `Toast`/`app-toast`/`data-bs-delay` markers present (or the agreed `toast_panel()` markup).
3. `test_no_alert_in_htmx_handler_returns` — source-level grep test (like the existing remediation tests) asserting no `return Alert(` inside `@app.get/post` HTMX `/ui/*` handlers in `exams.py`, `ops.py`.
4. Wizard auto-title test (Phase 3), notifications-prefs test (Phase 2), ARIA tests (Phase 4).

### 5.2 Documentation updates

- `QUICK_REFERENCE.md` — add a "HTMX response rules" reminder box:
  - In-place HTMX swap → `toast_panel()` / `show_toast()` / `EmptyState`.
  - Redirect flows → `push_flash()` → `pop_flash()` in shell.
  - Never return `Flash(...)` from an `/ui/*` handler.
- `FRONTEND_SPEC.md` — update Settings tab list (5–6 tabs), note Integrations descope (§6.12), note proposal-detail-as-collapse decision, wizard auto-title behavior.
- This file — add completion log at the bottom (checkboxes per item, date, test result).

### 5.3 Final verification checklist (run in order)

```powershell
cd C:\Users\Meshell\Desktop\FastHTML\skuphase
# 1. Full suite
..\.venv\Scripts\python.exe -m pytest tests/ -q --no-header          # expect: all pass (151 + new)
# 2. Source-level guarantee
Select-String -Path 'app\frontend\routes\*.py','app\frontend\components\*.py' -Pattern 'return Flash\('   # expect: 0 in HTMX handlers
Select-String -Path 'app\frontend\routes\exams.py' -Pattern 'return Alert\('                              # expect: 0
# 3. App boots
..\.venv\Scripts\python.exe -c "from app.main import app; print('routes:', len(app.routes))"
# 4. Manual smoke (uvicorn app.main:app --reload)
#    - login as demo admin → exams list → open exam → run preflight → export → delete
#    - 375px viewport: bottom nav, offcanvas menu, toasts above nav
#    - print preview of exam detail: no split questions
```

### 5.4 Out-of-scope / explicitly not fixing (recorded for traceability)

- Documents / Assets / RAG Search nav items — removed by design.
- Prototype JSS/SS grade list — spec's primary levels win.
- Dedicated proposal detail page — collapse accepted (this plan documents it); revisit only if user feedback demands.
- API & Integrations real backend — stub/descope per Phase 2 decision.

---

## Kickoff Order & Dependency Notes

1. **Phase 1 first**: the `show_toast` conversion pattern established there (and the existing `show_toast` call at `exams.py:1866` as reference) is the template everything else follows; `_wizard_error` is used by 3 sites, fix it once.
2. **Phase 1** touches only `exams.py` + `ops.py` — no cross-phase conflicts.
3. **Phase 2** needs a backend decision (prefs endpoint) before frontend work; if backend is delayed, ship Phase 2.2 stub first.
4. **Phase 3 + Phase 4** are independent of each other; can run in either order or parallel.
5. **Phase 5** must be last; the grep gate in 5.3 is the definition of done for Phase 1.

**Estimated total: 3–4 focused days.**

---

## Completion Log

| Item | Status | Date | Notes |
|---|---|---|---|
| 1.1 6× Flash-in-HTMX → show_toast | ☐ | | |
| 1.2 4× ephemeral Alert → show_toast | ☐ | | |
| 1.3 Keep-as-is exceptions commented | ☐ | | |
| 1.4 QUICK_REFERENCE feedback rule | ☐ | | |
| 1.5 Phase 1 tests | ☐ | | |
| 2.1 Notifications tab + prefs API | ☐ | | |
| 2.2 Integrations stub/descope decision | ☐ | | |
| 3.1 Dashboard curriculum CTA | ☐ | | |
| 3.2 Wizard auto-title | ☐ | | |
| 3.3 Poll copy + aria-live | ☐ | | |
| 3.4 UNDER_REVIEW teacher copy | ☐ | | |
| 3.5 Proposals explainer | ☐ | | |
| 4.1–4.9 ARIA / mobile / print / copy | ☐ | | |
| 4.9 Contrast check result | ☐ | | |
| 5.1 Regression tests | ☐ | | |
| 5.2 Docs updated | ☐ | | |
| 5.3 Final verification (pytest result) | ☐ | | |
## Completion Log — Phase 2 (in progress) — EmptyState bug fix ✅ (2026-09-04)

**Latent bug discovered during Phase 2 implementation:** every `EmptyState(...)` call in the
frontend passed `message=` / `primary_cta=`, but faststrap's real signature is
`(icon, title, description, action, ...)` — the wrong kwargs fell into `**kwargs` and became
silently swallowed HTML attributes. Result: **no empty-state description text or CTA button
ever rendered anywhere in the app** (6 affected call sites).

Fixed all 6 sites to use `description=` / `action=`:
- `bank.py:403–407` — "No questions in bank yet" + View Exams CTA
- `exams.py:361–370` — "No exams yet" + Create exam CTA
- `exams.py:638–648` — "Preflight not yet run" + Run Preflight Check CTA
- `exams.py:705–708` — "Quality report not available" description
- `proposals.py:309–313` — "No proposals found" + Submit Proposal CTA
- `settings.py:200–212` — API & Integrations stub + Contact Support CTA (new Phase 2 tab)

Verification: py_compile clean on all 4 touched files; EmptyState render smoke test confirms
description + action now appear in markup; `Button(as_=...)` confirmed valid.

Regression guard added (`tests/test_audit2_phase1.py`):
- `test_emptystate_calls_use_description_and_action_kwargs` — source scan so `message=`/
  `primary_cta=` can never reappear in route files
- `test_emptystate_renders_description_and_action` — render-level pin of correct output

**Suite: 163 passed** (151 original + 10 Phase 1 + 2 EmptyState regression).

Remaining Phase 2 work: notifications-tab handler polish + tab-rail acceptance check
(most of the tab already exists in settings.py from earlier in this session).

## Completion Log � Phase 2 ? (2026-09-04)
All Phase 2 items implemented and verified:

**Backend**
- `app/models/user.py`: `notification_prefs` JSON column (server_default of 6-key dict with prototype defaults).
- `app/schemas/auth.py`: `NotificationPrefs` (6 bools) + `PreferencesResponse`.
- `app/api/v1/auth_router.py`: `GET /auth/me/preferences` + `PUT /auth/me/preferences` (auth-required, per-user).

**Frontend (settings.py)**
- Tab rail now 6 tabs: Profile, Account, **Notifications** (new), **API & Integrations** (new stub), Policy, Security.
- Notifications tab: 6 switches seeded from saved prefs (defaults ON/ON/ON/OFF/OFF/ON per prototype), `Save Preferences` CTA.
- POST `?tab=notifications` handler placed BEFORE the school-admin gate (per-user pref, works for individual teachers); unchecked boxes -> False; PUT then 303 redirect with flash; failure flash surfaces backend message.
- Integrations tab: coming-soon EmptyState + Contact Support CTA; descope note in FRONTEND_SPEC.

**Latent bug fixed (found during Phase 2)**
- All `EmptyState(message=..., primary_cta=...)` call sites were silently passing wrong kwargs
  (faststrap signature is `title=`/`description=`/`action=`), so empty-state text and CTAs never rendered.
- Fixed in: exams.py (3 sites), bank.py (1), proposals.py (1), settings.py (new code used correct signature).
- Added render smoke test in test_audit2_phase1.py.

**Tests**
- New: tests/test_audit2_phase2.py � 7 tests (tab rail, 6 toggles render, seeded checked-state,
  PUT payload exact-match incl. unchecked->False, individual-teacher save, failure flash, integrations stub).
- **Final suite: 170 passed** (161 after Phase 1 + 2 EmptyState smoke + 7 Phase 2). py_compile clean.

## Completion Log — Phase 3 ✅ (2026-09-04)
All Phase 3 items implemented and verified:

- Dashboard curriculum-first CTA card (dashboard.py:349–363): always-shown hero card with
  "Start from the curriculum" + "Open Curriculum Explorer" deep-link to /app/curriculum.
- Wizard auto-title (exams.py Step 1 form): title input pre-filled from class_level/subject/term
  query params as "{class_level} {subject} — {term} Examination" (+ "(Week N)" when weeks present).
- Polling time expectation + aria-live (exams.py:1813–1818): "usually takes under 2 minutes"
  copy + aria-live="polite" on the poll fragment container.
- UNDER_REVIEW helper copy for teachers (exams.py detail action bar): teachers see
  "with your school admin for approval" on final_submitted_by_teacher exams; admins do not.
- Proposals explainer empty-state (proposals.py list route): zero-proposal schools see
  "How proposals work" + workflow description + "New Proposal" CTA.
- New tests: test_audit2_phase1.py Phase 3 block — 5 tests (dashboard CTA, poll time+aria,
  proposals explainer, teacher waiting copy, admin no-waiting-copy).
- **Final suite: 175 passed.** py_compile clean on all touched files.
## Completion Log — Phase 4 ✅ (2026-09-04)

All Phase 4 items implemented, tested, and verified:

- **4.1 ARIA `aria-current` on active pills/tabs** — exam list filter pills (`exams.py` `_pill`, active only; verified count == 1 in rendered page), curriculum class/subject/term pills, settings tab links.
- **4.2 Toggle controls → RESOLVED: native checkboxes, no aria-pressed** — the show-answers toggle and Bloom's pills are already real labeled `<input type=checkbox>` elements (checked state natively exposed, visibly styled via `custom.css`). Per ARIA guidance, `aria-pressed` would *mask* the checkbox role, so it was deliberately not added; a regression test locks in the guarantee (`test_question_toggles_are_native_checkboxes`).
- **4.3 Toast container mobile clearance** — `#app-toast-container` bottom offset raised above the bottom nav in `custom.css` (`@media max-width: 991.98px`).
- **4.4 Filter-pill tap targets on small screens** — py-bumped pills under `575.98px`.
- **4.5 Print: page-break-inside: avoid** — `.print-avoid-break` utility in the print block; question rows carry `print-avoid-break` (`components/exam.py:235`).
- **4.6 Proposal header title clamp** — `text-truncate` + max-width (`proposals.py:174`).
- **4.7 hx-indicator on small partials** — comments tab + exports-history tab triggers.
- **4.8 Action-oriented fallback error copy — CENTRALIZED in `unwrap()` (`api.py`)** — discovered `unwrap`'s bare status-code net ("Server returned error code 500. Please try again.") was overriding every per-route fallback string everywhere. Updated `unwrap` case 6 & case 8 nets to plain-language, action-oriented copy ("We could not complete that request … please try again in a moment."). Backend `message`/`detail` payloads still take precedence. Fixes every error path at once, not just exam flows.
- **4.9 Contrast check** — still open as a manual pass (live eyedropper on brand-tint cards); no code risk.
- **4.10 Tests** — `tests/test_audit2_phase4.py` = 6 tests (active-pill aria on exams list / curriculum / settings, load-fallback copy, delete toast + fallback copy, native-checkbox toggles).

**Final suite: 181 tests collected — all passing (exit code 0), py_compile clean.**
Audit2 test totals: phase1 = 17, phase2 = 7, phase4 = 6 → 30 regression tests added (151 baseline → 181).
