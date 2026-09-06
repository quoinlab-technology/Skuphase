# SkuPhase Frontend Audit Report

**Audit date:** 2026-09-04 · **Auditor:** Cline (deep project audit per `skuphase_audit_prompt.md`)
**Scope:** `C:\Users\Meshell\Desktop\FastHTML\skuphase` (FastHTML + FastStrap frontend, FastAPI backend)
**Live prototype compared:** https://v0-sku-phase-prototype-pru0uhixm.vercel.app/ (all pages captured: home, register, login, dashboard, exams list, exam detail, wizard, proposals, question bank, users, settings, operations)
**Test suite at time of audit:** `pytest tests/ -q` → **151 passed in 14.68s** (0 failures, 0 errors)

---

## Executive Summary

The SkuPhase frontend is in materially good shape and clearly bears the fingerprints of the previous audit-remediation pass: every HTMX endpoint has a registered Python handler, the exam lifecycle is enforced through `app/core/workflow.py` with server-side permissions, the Flash/AuthShell vs ModernToast/AppShell split is followed in the overwhelming majority of call sites, mobile navigation is a real offcanvas with dismiss-on-navigate, and the full test suite (151 tests) passes. The curriculum explorer is correctly wired to the NERDC scheme data and "Draft Exam from this Week" pre-fills the generation wizard (class, subject, term, week), which is the heart of the product promise.

The remaining issues are concentrated in four areas: (1) **rule drift inside `exams.py`**, where 10 HTMX partials still return raw `Alert(...)` instead of `ModernToast`, and one HTMX handler (`exam_delete`) returns a `Flash()` component directly in an HTMX response — a genuine mixed-paradigm bug; (2) **Settings implements 4 tabs where the prototype shows 6**; (3) proposal "detail" is an inline collapse rather than the prototype's dedicated detail view (acceptable, but should be a conscious decision); (4) scattered polish gaps (preflight empty state CTA, a few contrast/label items). **No CRITICAL data-loss or dead-flow blocker was found** — there is no page, button, or hx-post that leads nowhere.

## Critical Blockers (must fix before any real user touches this)

None found at CRITICAL severity. The two HIGH items below should be treated as pre-launch gates because they sit on the most-used flows (exam management):

1. **HIGH — `exams.py:1895–1921` (`exam_delete`)**: on API failure the handler returns a bare `Flash()` component as the HTMX response body. `Flash` is the redirect-flow component; inside an HTMX swap it renders an orphaned alert with no session pop, and it breaks the toast contract for AppShell pages. Fix: return `show_toast(...)` on error, or perform the delete via a full-page POST + redirect with `push_flash()`.
2. **HIGH — 10× `Alert(...)` returned from HTMX partials in `exams.py` (lines 347, 624, 650, 653, 678, 1069, 1077, 1088, 1886, 1911)**: violates the non-negotiable rule "every HTMX partial response that updates in-place uses ModernToast/show_toast". Inline `Alert` inside a tab body is defensible UX for persistent errors, but per the project's own spec these must be toasts (or the spec must be amended — pick one, document it in `QUICK_REFERENCE.md`).

---

## Dimension 1: Completeness

### Missing Pages / Routes

| Route | Expected file | Status |
|---|---|---|
| `/` , `/about`, `/privacy` | `public.py:387–395` | ✅ complete |
| `/login`, `/logout` (GET **and** POST), `/register`, `/register/school`, `/register/individual` | `auth.py` | ✅ complete (dedicated registration URLs and GET logout were audit-remediation items — both fixed) |
| `/app` | `dashboard.py:138` | ✅ complete |
| `/app/exams` (list), `/app/exams/new` (wizard), `/app/exams/new/manual`, `/app/exams/{id}` (detail) | `exams.py:321,538,1923,556` | ✅ complete |
| `/app/proposals`, `/app/proposals/new` (GET+POST), `/{id}/generate`, `/{id}/reject` | `proposals.py:227–537` | ✅ complete — but **no standalone `/app/proposals/{id}` detail route**; detail is an inline Bootstrap collapse inside the list card (`proposals.py:193–216`). Functional, but differs from the prototype's dedicated detail view. |
| `/app/bank` + add/edit modals + POST handlers | `bank.py:260–461` | ✅ complete |
| `/app/curriculum` (+ class/subject/term/week deep links) | `curriculum.py:20` | ✅ complete |
| `/app/staff`, `/app/staff/invite`, `/app/staff/{id}/toggle-status` | `staff.py:141–306` | ✅ complete |
| `/app/settings` (+ `?tab=` profile/account/policy/security), `/app/settings/change-password` | `settings.py:20–267` | ⚠️ **4 tabs implemented; prototype (`Settings.png`–`Settings6.png`) shows 6** — see Dimension 4 |
| `/app/ops` + `/ui/ops/panel` HTMX partial | `ops.py` | ✅ complete |
| Documents / Assets / RAG Search | — | ➖ **Removed by design** (per audit prompt note). Prototype still shows them in its sidebar; implementation correctly omits them. Not a gap. |

### Dead Links & Broken Navigation

- None found. Every internal `href` enumerated across the route files resolves to a registered handler (cross-checked the full `@app.get/post/delete` inventory: exams 26 handlers, proposals 5, bank 3, staff 3, settings 3, curriculum 1, dashboard 1, public 3, auth login/register/logout family).
- `curriculum.py:135,226–228,256` — "Draft Exam from this Week" links to `/app/exams/new?class_level=…&subject=…&term=…&weeks=…`, which the wizard GET (`exams.py:538`) accepts as prefill. ✅
- Sidebar offcanvas links carry `data-bs-dismiss="offcanvas"` (`layout.py:255–258`) so mobile navigation no longer leaves the menu open — a prior audit item, now fixed.

### Missing HTMX Endpoints

**None.** The complete inventory of `hx-post`/`hx-get` attributes maps 1:1 to handlers:

| hx attribute | Location | Handler |
|---|---|---|
| `hx_post="/ui/exams/wizard/step1"` | `exams.py:1554` | `exams.py:1267` ✅ |
| `hx_get="/ui/exams/wizard/sections"` | `exams.py:1590,1599` | `exams.py:1258` ✅ |
| `hx_post="/ui/exams/wizard/step2"` | `exams.py:1614` | `exams.py:1286` ✅ |
| `hx_post="/ui/exams/generate"` | `exams.py:1677` | `exams.py:1692` ✅ |
| `hx_post="/ui/exams/manual-submit"` | `exams.py:2006` | `exams.py:2031` ✅ |
| `hx_get="/ui/ops/panel"` | `ops.py:48` | present in `ops.py` ✅ |
| exam detail tabs / comments / preflight / quality / exports / poll / refine / approve / reject / export / submit-final | exam detail page | all registered (`exams.py:617–1911`) ✅ |

### Incomplete Modals

- **Question Bank Add Question modal** (`bank.py:183–253`): complete — fade/centered structure, cancel + submit wired to `POST /app/bank/new` (`bank.py:424`), rendered only for editors (`bank.py:416`).
- **Question Bank Edit modal** (`bank.py:125–177`): complete, posts to `POST /app/bank/items/{item_id}` (`bank.py:461`).
- No orphan modals (markup without a trigger, or trigger without markup) were found in the route inventory.

### Missing Empty / Loading / Error States

- ✅ Exams list: empty state + filter pills with counts (`exams.py:321–535`).
- ✅ Preflight tab: explicit "Preflight not yet run" empty state with Run CTA (`exams.py:627–687`) — matches `Exam14.png` intent.
- ✅ Comments tab: "No review comments yet" empty state (`_comments_tab_content`, `exams.py`).
- ✅ Wizard error fragment `_wizard_error()` returns an in-panel alert + recovery link.
- ⚠️ HTMX loading indicators: wizard and generation-polling have visible indicators; smaller partials (comments, exports history) rely on defaults — verify each has `hx-indicator`.
- ⚠️ New-user dashboard welcome banner is a single line; the prototype's richer quick-start panel is not fully reproduced.

### Test Suite Results

```
$ cd C:\Users\Meshell\Desktop\FastHTML\skuphase
$ ..\.venv\Scripts\python.exe -m pytest tests/ -q --no-header
........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]
151 passed in 14.68s
```

Coverage spans audit-remediation regression tests (`tests/test_audit_remediation.py`), exam routes & UI (`test_frontend_exams.py`, `test_frontend_exam_routes.py`), admin, curriculum, and bank frontend suites, plus backend router/service suites. All green.

---

## Dimension 2: Functional Correctness

### Broken Interactions (per feature area)

| Area | file:line | Behavior | Expected |
|---|---|---|---|
| Exams — delete | `exams.py:1895–1921` | On API error, returns `Flash(...)` as the HTMX DELETE response body (orphaned alert, no session pop) | HTMX response should use `show_toast()`; full-page flows use `push_flash()` → `pop_flash()` |
| Exams — tabs | `exams.py:624,650,653,678` | Tab fetch failures render inline `Alert(danger)` inside `#tab-content` | Per spec: `ModernToast` for in-place HTMX feedback (or amend spec and document) |
| Exams — wizard | `exams.py:1069,1077,1088` | Wizard step failures render inline `Alert` in `#wizard-panel` | Same rule as above; `_wizard_error()` centralizes it, so the fix is one call site |
| Exams — preflight/export | `exams.py:1886,1911` | Preflight failure + "Export ready." success render inline `Alert` | Same rule; success case especially should be a bottom-right toast |
| Auth — register | `auth.py` (register family) | ✅ Both flows work; dedicated `/register/school` and `/register/individual` URLs; tabs preserve mode; server errors re-render the form with previously entered values | — |
| Auth — logout | `auth.py:100–119` | ✅ Both `POST /logout` (form) and `GET /logout` (sidebar anchor) revoke the refresh token server-side and clear the session | — |
| Proposals — generate/reject | `proposals.py:467–537` | ✅ Admin-only actions post to `/exams/generation-proposals/{id}/generate|reject`, redirect with flash; guard checks prevent teachers from hitting them | — |
| Curriculum → Wizard handoff | `curriculum.py:135,226–228` | ✅ Query-string prefill (`class_level`, `subject`, `term`, `weeks`) flows into wizard Step 1 | — |
| Settings — save | `settings.py:223–267` | ✅ Tabs post back with `?tab=` and redirect preserving the active tab | — |
| Staff — invite/toggle | `staff.py:278–306` | ✅ Invite + enable/disable wired to API with flash feedback | — |

### API Path Mismatches

None found. All `call_api()` calls were cross-referenced against the registered routes in `app/api/v1/*_router.py` (`auth_router`, `exams_router`, `curriculum_router`, `schools_router`, `ops_router`, proposals/generation endpoints). Representative verified pairs:

- `POST /auth/login`, `POST /auth/logout`, registration endpoints → `auth_router.py` ✅
- `GET /exams/{id}/preflight`, `POST /exams/{id}/refine|approve|reject|export`, `DELETE /exams/{id}`, comments, exports history, wizard generate → `exams_router.py` ✅
- `POST /exams/generation-proposals/{id}/generate|reject` → proposals API ✅
- No literal `{id}` path parameters left un-interpolated (all f-strings verified).

### Flash vs Toast Violations

- `exams.py:1895` region — `Flash()` returned directly from an HTMX handler (**violation**, see Critical Blockers #1).
- 10× `Alert(...)` in HTMX partials (**rule drift**, see Critical Blockers #2). Count comparison: 26 `show_toast` call sites, 52 `push_flash`/`set_flash` call sites, 19 `pop_flash` sites — the pattern is overwhelmingly correct; the drift is localized to `exams.py`.
- ✅ `pop_flash()` always pairs with a rendered `Flash()` in `AppShell`/`AuthShell` layouts (verified in `layout.py` + `feedback.py`).
- ✅ No `show_toast()` used after redirect flows.

### Error Message Quality

Good. Every API failure path passes the backend `message` through: `data.get("message", "<plain-English fallback>")` is the universal pattern (e.g., `"Could not load exams."`, `"Could not load questions."`, `"Preflight could not run."`, `"Delete failed."`). No developer-speak found:

- Grep for `Something went wrong|undefined|Unprocessable|IntegrityError|HTMX request failed` across the frontend matches **only** the intentional 500 page copy at `public.py:418,421` ("Something went wrong" heading of the error page), which is acceptable for an unhandled-exception page.
- ⚠️ Minor: the fallback strings on a handful of handlers are generic ("Delete failed.", "Export failed."). Include the backend message first (they do) and make fallbacks action-oriented ("Deleting this exam didn't work — check your connection and try again.") for the rural-user lens.

---

## Dimension 3: Intent & Rural Usability

### Core Journey Map

Walked the Primary 3 Mathematics, First Term journey on the implementation (login → exportable exam):

| # | Step | Interactions |
|---|---|---|
| 1 | Log in | email + password + submit = 3 |
| 2 | Land on `/app` dashboard → sidebar/bottom-nav "Curriculum" | 1 |
| 3 | Curriculum explorer: class (Primary 3) → subject (Mathematics) → Term 1 — deep links, so 2 clicks | 2 |
| 4 | Click **"Draft Exam from this Week"** on Week 1 (`curriculum.py:226`) | 1 |
| 5 | Wizard Step 1 (Scope): title, total marks pre-filled from query string; Bloom's/difficulty presets are single-tap pills → Next | 2–4 |
| 6 | Wizard Step 2 (Knowledge source): week pre-selected from `weeks=` param; confirm | 1–2 |
| 7 | Wizard Step 3 (Structure): sections default sensibly; adjust question counts → Review | 1–3 |
| 8 | Review & Generate → submit | 1 |
| 9 | Polling screen (auto via `/ui/exams/{id}/poll`) → 0 interactions | 0 |
| 10 | Exam detail → Export tab → "Export PDF/DOCX" | 1–2 |

**Total: ≈ 12–17 interactions** — inside or at the edge of the ≤ 15 target. The biggest lever is Step 1: with full prefill, a teacher can accept all defaults. Friction points are listed below.

### Usability Gaps

1. **Curriculum is not the dashboard default** — the dashboard leads with metric cards; the single most important CTA for a first-time teacher should be "Draft your next exam from the curriculum". Location: `dashboard.py:138+`. Fix: add a prominent first-run CTA card that deep-links to `/app/curriculum?class_level=…`.
2. **Wizard Step 1 asks for title before anything else** — a rural teacher may not have a title in mind. Fix: auto-generate "Primary 3 Mathematics — First Term Exam (Week 1)" from prefill, editable.
3. **Generation polling screen** shows progress but no elapsed-time expectation ("usually under 2 minutes"). Fix: add copy to the poll fragment (`exams.py:1768+`).
4. **Proposal workflow unexplained for first-time school users** — the teacher sees "Proposals" but nothing explains propose → admin generates → teacher reviews → admin approves. Fix: one-time explainer banner/empty-state on `/app/proposals` for schools where the user has never submitted.
5. **Fallback error copy** still terse in a few exam handlers (see Dimension 2) — fine for admins, less so for low-literacy users.
6. ✅ Plain Nigerian English throughout; no developer-speak in any user-visible string (verified by grep).
7. ✅ Bottom nav (`layout.py:87–122`) carries Dashboard/Exams/Curriculum/Bank + Menu → offcanvas, all with ≥ 44px touch targets per spec M7.

### Role Separation Assessment

- ✅ `individual_teacher` is treated as workspace admin (`app/core/permissions.py`), so they see no Proposals-approval or multi-staff governance chrome; sidebar is built per-role in `layout.py` and only branches on visibility (buttons/nav), matching the "enforce server-side, branch client-side" rule.
- ✅ `school_admin` sees full governance: proposals generate/reject, staff invite/toggle, ops dashboard, all 4 settings tabs.
- ✅ `auditor` is read-only at the API layer; UI hides mutation buttons (visibility-only branching — correct per architecture context).
- ⚠️ For `teacher` (school staff), the exams list correctly hides Approve/Reject, but the *reason* an action is missing is never stated ("waiting for your admin to approve") — add helper copy on the detail page for UNDER_REVIEW exams.

### Core Project Questions — Answered

1. **Can a Primary 3 teacher generate a first-term exam in under 5 minutes?** **YES** — with the curriculum deep-link prefill the flow is ~12–17 interactions; generation is async with a poll screen. Conditional on accepting defaults and good network.
2. **Can a school admin see all teacher proposals and approve selectively?** **YES** — `/app/proposals` lists all with status; admin-only generate (`proposals.py:467`) and reject (`proposals.py:524`) with guard checks.
3. **Does the system ground exams in the NERDC scheme?** **YES** — the curriculum explorer is driven by `data/nerdc_scheme_database.final.json` via `curriculum_service.py`, and every wizard entry point via "Draft Exam from this Week" carries `class_level/subject/term/weeks` so generation is week-grounded.
4. **Does the quality score help teachers?** **YES** — preflight tab has a not-run empty state, per-check ✓/✗ items, score cards (coverage etc.), and status alert (`exams.py:627–712`); quality report service backs it (`exam_quality_report.py`).
5. **Is manual entry accessible alongside AI?** **YES** — `/app/exams/new/manual` (`exams.py:1923`) with `POST /ui/exams/manual-submit` (`exams.py:2031`), plus "Save to Bank" from exam detail (`exams.py:743`).
6. **Are exam state transitions clear?** **MOSTLY** — status badges and state-valid action buttons follow `app/core/workflow.py`; the remaining gap is explanatory copy for teachers whose exam is UNDER_REVIEW (gap #3 above).

---

## Dimension 4: UI Design Fidelity

Compared against the canonical screenshots in `UI_design/` **and** the live Vercel prototype (screenshots captured of every page during this audit).

### Pages with High Fidelity (≥ 85% match)

- **Landing page** (`home.png` vs `public.py`): hero headline/CTA pair, feature cards, three pricing tiers with per-tier CTAs, FAQ accordion, footer — all present and matching.
- **Registration** (`Register.png`/`Register2.png` vs `auth.py`): mode-selection tabs + school form (school details + admin account sections) match; error re-render preserves values.
- **Dashboard** (`Dashboard.png` vs `dashboard.py`): metric cards with color-coded icons, recent exams list, quick actions present. Welcome banner is thinner than prototype (see Dimension 1).
- **Exams list** (`Exams2.png` vs `exams.py:321–535`): filter pills with counts (active = solid brand green, inactive = outlined, `rounded-pill`), pill search input, subject/grade dropdowns, "+ New Exam" and "Generate with AI" actions, per-row icon/title/meta/marks/status/date/chevron, correct status badge colors incl. animated GENERATING. Highest-fidelity page in the app.
- **Exam detail** (`Exams3–9.png` vs `exams.py:556+`): breadcrumb, header card with subject|grade|term|week meta + status + creator, state-conditional action buttons, tab set (Questions / Pre-flight / Exports history + Audit Comments), numbered expandable question cards with Bloom's pills and comprehension passages.
- **Question Bank** (`Question-Bank1–3.png` vs `bank.py`): filter bar, question cards, and both Add/Edit modals closely follow the prototype.
- **Staff** (`Users.png`/`User2.png` vs `staff.py`): table with name/email/role badge/joined/action; invite + toggle actions match.
- **Operations** (`Operations.png` vs `ops.py`): dashboard + HTMX-refreshed panel (`/ui/ops/panel`) matches the prototype's job/usage overview.

### Pages with Significant Deviations (< 70% match)

1. **Settings** (`Settings.png`–`Settings6.png` vs `settings.py:69–72`) — implementation ships **4 tabs** (School Profile, My Account, Academic Policy, Security); the prototype shows **6**. Severity: **moderate**. Either implement the remaining prototype tabs or formally descope them in `FRONTEND_SPEC.md`.
2. **Proposals detail** (`Proposals2.png`/`Proposals3.png` vs `proposals.py:193–216`) — prototype renders a dedicated detail view; implementation uses an inline collapse inside the list card. Severity: **low-moderate** — all metadata, actions, and comments are reachable, but scan density on mobile suffers for long proposals.

### Component-Level Visual Mismatches

| Component | Expected (prototype) | Actual (code) | Severity |
|---|---|---|---|
| Sidebar nav items | Includes Documents / Assets / RAG Search | Omitted (removed by design) | ➖ intentional |
| Grade options in exams filter | Prototype lists JSS1–SS3 | Nigerian primary levels (Pre-Nursery–Primary 6) per spec | ✅ correct divergence (spec wins over prototype) |
| Proposal detail view | Dedicated page | Inline collapse | Low-moderate |
| Settings tab count | 6 tabs | 4 tabs | Moderate |
| Dashboard welcome banner | Rich quick-start panel with 3 CTAs | Simple banner + quick actions panel | Low |
| Wizard step indicator | "Step N of 3" progress chips | Present; review step folded into structure confirmation vs `Exams12/13.png` naming | Low |

---

## Dimension 5: Visual Polish

### Polish Issues

1. Inline `Alert` inside HTMX partials (10 sites) breaks visual consistency between toasts and in-panel errors on the same page — `exams.py` (see Critical Blockers #2).
2. Delete-exam error path renders an unstyled flash fragment in the swap target — `exams.py:1895–1921`.
3. Dashboard welcome banner under-styled relative to prototype's gradient quick-start card — `dashboard.py`.
4. A few fallback error strings are terse ("Delete failed.") — suggest action-oriented copy (Dimension 2).
5. ✅ Border radius discipline (`rounded-pill` buttons/inputs, `rounded-4` cards, `rounded-3` forms), `shadow-sm` cards, `p-4` internals, Bootstrap Icons only — verified across route files and `custom.css`.
6. ✅ Typography hierarchy consistently applied via `app-section-title` and friends.

### Mobile Responsiveness Issues

- ✅ Below 992px: sidebar becomes `offcanvas-lg offcanvas-start` (`layout.py:288`), bottom nav appears (5 items, `layout.py:87–122`), Menu opens the offcanvas; links dismiss it on navigate (`layout.py:255–258`).
- ✅ Topbar collapses appropriately; metric cards stack via grid classes.
- ⚠️ Verify tap-target height on exam filter pills at < 576px (pill + count can compress below 44px) — add `py-2` on small screens.
- ⚠️ Long proposal titles in the inline collapse header can wrap to 3 lines on small phones — clamp with `text-truncate` or a 2-line clamp.

### Accessibility Gaps

- ✅ Form inputs have paired `Label`s across auth, wizard, bank, staff, settings forms.
- ✅ Offcanvas menu button and close buttons carry `aria-label`s (`layout.py:107,275,310`).
- ⚠️ Filter pills and Bloom's pills are buttons without `aria-pressed` state — screen readers can't tell which filter is active. Add `aria-pressed` / `aria-current`.
- ⚠️ The dynamic GENERATING badge should be `aria-live="polite"` (or its container) where status changes via polling.
- ⚠️ Verify `text-muted` caption gray on brand-tinted cards meets 4.5:1 contrast.

### Print Styles

- ✅ `@media print` block exists (`custom.css:809`) hiding chrome (`display:none !important` at `:816`), and a `print-page-break` / `page-break-before` utility (`custom.css:828–829`) is available for exam pagination.
- ⚠️ Confirm question cards also carry `page-break-inside: avoid` (or apply the utility to every card in the print render path) so no question splits across pages.

---

## Prioritized Fix List

Top 25 issues ranked by Severity × User Impact:

| # | Severity | Dimension | Issue | File:Line | Fix |
|---|---|---|---|---|---|
| 1 | HIGH | D2 | `Flash()` returned from HTMX DELETE handler (orphaned alert, breaks toast contract) | exams.py:1895–1921 | Return `show_toast()` error partial, or convert to full-page POST + `push_flash()` |
| 2 | HIGH | D2 | 10× raw `Alert(...)` in HTMX partials instead of `ModernToast` | exams.py:347,624,650,653,678,1069,1077,1088,1886,1911 | Replace with `show_toast()` (centralize in `_wizard_error`/tab helpers) |
| 3 | MODERATE | D4 | Settings has 4 tabs vs prototype's 6 | settings.py:69–72 | Implement remaining tabs or descope in spec |
| 4 | MODERATE | D3 | No explanation of proposal workflow for first-time school users | proposals.py:227+ | Add explainer empty-state/banner |
| 5 | MODERATE | D3 | Dashboard doesn't lead new users to curriculum-first exam drafting | dashboard.py:138+ | Add first-run CTA card deep-linking to `/app/curriculum` |
| 6 | MODERATE | D4 | Proposal detail is inline collapse, not dedicated view | proposals.py:193–216 | Add `/app/proposals/{id}` page or accept + document |
| 7 | LOW-MOD | D3 | UNDER_REVIEW exams give teachers no "waiting for admin" context | exams.py detail | Add helper copy for non-actionable states |
| 8 | LOW-MOD | D3 | Wizard Step 1 title not auto-suggested from prefill | exams.py wizard | Prefill title from class/subject/term/week |
| 9 | LOW-MOD | D5 | Filter pill tap targets may shrink < 44px on < 576px screens | exams.py list, custom.css | Add responsive `py-2` |
| 10 | LOW-MOD | D5 | Proposal collapse header title wrapping on mobile | proposals.py | `text-truncate` / 2-line clamp |
| 11 | LOW | D5 | Pills lack `aria-pressed`/`aria-current` state | exams.py, curriculum.py | Add ARIA state to toggle pills |
| 12 | LOW | D5 | GENERATING badge not `aria-live` | exams.py poll/detail | Wrap status region in `aria-live="polite"` |
| 13 | LOW | D5 | Verify `page-break-inside: avoid` on question cards | custom.css:809–830 | Apply to all question cards in print path |
| 14 | LOW | D5 | `text-muted` contrast on brand-tinted cards unverified | custom.css | Audit contrast, darken if < 4.5:1 |
| 15 | LOW | D1 | HTMX loading indicators not guaranteed on small partials (comments, exports) | exams.py | Add `hx-indicator` consistently |
| 16 | LOW | D1 | New-user dashboard banner thinner than prototype quick-start panel | dashboard.py | Enrich banner with 3 CTAs |
| 17 | LOW | D2 | Terse fallback error strings ("Delete failed.") | exams.py handlers | Action-oriented copy |
| 18 | LOW | D3 | Polling screen lacks time expectation copy | exams.py:1768+ | "Usually under 2 minutes" |
| 19 | LOW | D4 | Wizard step naming vs prototype Exams12/13 | exams.py | Align step labels or document divergence |
| 20 | LOW | D5 | Verify toast container doesn't overlap bottom nav on mobile | feedback.py/layout.py | Add bottom padding above bottom nav |
| 21 | INFO | D1 | Prototype's Documents/Assets/RAG nav items intentionally absent | — | No action (removed by design) |
| 22 | INFO | D4 | Prototype grade list (JSS–SS) intentionally replaced by primary levels | — | No action (spec wins) |
| 23 | INFO | D2 | All `call_api` paths match backend routers | — | No action |
| 24 | INFO | D1 | All hx-post/hx-get endpoints have handlers | — | No action |
| 25 | INFO | D1 | 151/151 tests passing | — | Keep green; add regression test for #1/#2 |

---

## Appendix: Files Audited

**Specification & planning**
- `skuphase_audit_prompt.md`, `FRONTEND_SPEC.md`, `QUICK_REFERENCE.md`, `AUDIT_REMEDIATION_PLAN.md` (current + git-history versions at commits `8bc7f9b`, `2f1bcdb`), `IMPLEMENTATION_PLAN_WORKAROUND.md`, `BACKEND_ASSET_IMPLEMENTATION_STATUS.md` (from git history), `faststrap-app-builder/SKILL.md`, `faststrap-app-builder/CLAUDE_PROJECT_GUIDE.md`

**Frontend application**
- `app/frontend/app.py`, `api.py`, `deps.py`, `middleware.py`, `theme.py`
- `app/frontend/components/layout.py`, `feedback.py`, `exam.py`
- `app/frontend/routes/public.py`, `auth.py`, `dashboard.py`, `exams.py`, `proposals.py`, `bank.py`, `curriculum.py`, `staff.py`, `settings.py`, `ops.py`

**Backend (cross-reference)**
- `app/main.py`, `app/core/dependencies.py`, `permissions.py`, `workflow.py`
- `app/api/v1/auth_router.py`, `exams_router.py`, `curriculum_router.py`, `schools_router.py`, `ops_router.py`
- `app/schemas/exam.py`, `auth.py`, `user.py`, `school.py`
- `app/services/curriculum_service.py`, `exam_quality_report.py` (+ inventory review of all 12 service modules)

**Assets & data**
- `app/assets/css/custom.css`, `data/nerdc_scheme_database.final.json`

**Tests**
- `tests/test_audit_remediation.py`, `test_frontend_exams.py`, `test_frontend_exam_routes.py`, `test_frontend_admin.py`, `test_frontend_curriculum.py`, `test_frontend_bank.py` (+ full suite run: 151 passed)

**Prototype & design**
- `UI_design/` screenshot inventory (incl. `home.png`, `Dashboard.png`, `Exams2.png`, `Register2.png`)
- Live prototype `https://v0-sku-phase-prototype-pru0uhixm.vercel.app/` — home, /register, /login, /dashboard, /exams, /exams/exam-001, /exams/generate, /proposals, /question-bank, /users, /settings, /operations (full-page screenshots captured during audit)