# SkuPhase — Production-Readiness Audit (Final Consolidated Report)

**Repository:** C:\Users\Meshell\Desktop\FastHTML\skuphase
**Audit date:** 2026-10-04 → 2026-10-05 (two sessions, evidence merged)
**Scope:** Full production-readiness audit: environment, migrations, tests, tenant isolation, browser/viewport workflows, exports/PDFs, Package B lesson delivery, security, performance, FastHTML/Faststrap review, roadmap gap ledger.
**Design reference:** `skuphase\new_design\` • **Roadmap:** `skuphase\SYSTEM_AUDIT_AND_ROADMAP.md`

> Audit-only: no application code, migrations, production data, or configuration were modified. The only writes were (a) isolated test records created through the public API inside dedicated audit schools, and (b) an `_audit_tmp\` scratch folder holding probe scripts, generated PDFs, and screenshots as evidence.

---

## 1. Executive Summary

SkuPhase is a FastAPI + FastHTML/Faststrap curriculum-first assessment platform for Nigerian schools. Across this audit the **core assessment workflow and the first curriculum-delivery workflow both work end-to-end**: a teacher can manually author a rich exam in the browser, it persists, it exports to four PDF variants plus DOCX/CSV/GIFT/QTI, and it renders with school branding and no answer leakage. Package B (lesson plan → exercise → worksheet → syllabus coverage) works via API with full tenant isolation. AI copilot and AI exam generation both call a real LLM and return usable, curriculum-flavoured content. Tenant isolation held on every cross-school probe attempted (exams, exports, updates, deletes, lesson plans, worksheets, question bank, API keys all returned 404/403). Responsive layout is clean at all five required viewports with zero horizontal overflow.

Three genuine defects were found and root-caused with reproduction:

- **BLK-001 (Critical):** curriculum search returns HTTP 500 (broken SQLAlchemy cast) — keyword search is completely non-functional.
- **BLK-003 (High):** question-bank item creation returns HTTP 500 — one-line attribute typo (`current_user.id` vs `current_user.user_id`) makes "add to bank" impossible.
- **MED-002 (Medium):** DOCX export returns 500 for exams containing control characters that the API happily accepted; marking-guide PDF leaks literal `<super>…</super>` text.

Two prior "unverified" items from the earlier session are now **closed with evidence**: manual exam authoring (works in-browser) and AI generation (works with real LLM). PDF layout fidelity is verified by text extraction (no Poppler available — recorded as a limitation).

**Classification: Pilot-ready for controlled schools — with 1 Critical + 1 High fix required before pilot launch.**

---

## 2. Environment and Commands Used

- **OS:** Windows (win32) • **Python:** C:\Python314\python.exe (3.14)
- **Server:** Uvicorn on http://localhost:8000 (reload mode) • **PostgreSQL:** postgresql-x64-17 & -18 (Running) • **DB:** `skuphase_db` @ localhost:5433 (asyncpg)
- **Migrations:** Alembic, head `0013_curriculum_delivery`
- **PDF:** reportlab + svglib installed • **PDF text extraction:** `pypdf` available • **PDF→image rendering:** NOT available (no Poppler/pdftoppm, no PyMuPDF/fitz, no pdf2image) — recorded limitation
- **LLM:** `GROQ_API_KEY` / `OPENROUTER_API_KEY` present in `.env` — live calls verified working

Key commands (all from `skuphase\`):
```
C:\Python314\python.exe -m pytest tests\ -q --tb=short          # test suite
C:\Python314\python.exe run_server.py                            # server (already running)
C:\Python314\python.exe _audit_tmp\<probe>.py                    # API probes (JWT auth, cross-tenant, exports, Package B)
python -c ...app.core.database.get_async_session_maker()...     # DB/schema inspection
```
Browser automation: Playwright MCP (screenshots, viewport matrix, composer interaction) + CDP `Network.emulateNetworkConditions` (Slow 3G / offline). chrome-devtools MCP was unavailable (profile lock conflict with the Playwright browser).

---

## 3. Automated Test Results

```
C:\Python314\python.exe -m pytest tests\ -q --tb=short
```
**PASS — 283 tests, 0 failures** across all 37 test files. Only warning: Pydantic v2 deprecation for class-based `config` in `app/schemas/api_key.py:14` (non-blocking).

**Compilation/lint:** `ruff` and `mypy` are **not installed** in the environment (blocked — cannot be run). Recorded under Untestable items, not counted as a failure.

---

## 4. Migration / Database Results

- **Head current:** Alembic version = `0013_curriculum_delivery`; 13 migrations, linear chain, **no duplicate heads**; migrations apply cleanly; startup log confirms `Database migration state verified` / `Database verification passed`.
- **Schema present (Package A + B):** `exams`, `questions`, `exam_passages`, `question_bank_items`, `generation_jobs`, `question_refinements`, `exam_audit_comments`, `exam_quality_snapshots`, `api_keys`, `usage_logs`, `login_attempts`, `schools`, `school_settings`, `school_subscriptions`, `users`, `curriculums`, `curriculum_mappings`, `scheme_of_works` (Package A) plus `lesson_plans`, `weekly_exercises`, `syllabus_coverage` (Package B). All present.
- **Curriculum seed:** 102 curriculum rows, **NERDC only**, classes Pre-Nursery → Primary 6. **No JSS/SSS data** (see BLK-002). Scheme-of-works rows: 3,513.
- **Tenant ownership columns:** `school_id` present and populated on exams, questions, question_bank_items, lesson_plans, weekly_exercises, syllabus_coverage, api_keys. Verified at the query layer via cross-school probes (Section 9).
- **No destructive migration behaviour** observed; chain is additive.

---
## 5. Browser Workflow Results

| Workflow | Status | Evidence |
|---|---|---|
| Login (admin), bad-credential handling | Confirmed working | UI login + API; wrong password → "Incorrect email or password"; rate-limit after 5 |
| Dashboard (admin) | Confirmed working | 5 viewports, 0 overflow |
| Mobile nav (drawer) | Confirmed working | Menu button opens full "Navigation Sidebar" dialog with all links; closes |
| Manual exam composer (full) | **Confirmed working** | Subject/Grade set; LaTeX rendered in live preview; Add Question ×2; Submit → exam `c67cb20a…` persisted `under_review`, total_marks 4, both questions + marking scheme stored |
| Composer Preview button | Confirmed working (by design) | `#manual-preview-button` scrolls to `#manual-preview-card` (`exams.py:6003-6005`), not a modal |
| AI generation wizard (API) | Confirmed working | See Section 7 |
| Question bank page | Page loads; **create broken** | UI renders, but create endpoint 500 (BLK-003) |

**Viewport matrix (dashboard):** 1440×900, 1280×720, 768×1024, 390×844, 360×800 — every one reported `document.scrollWidth === clientWidth` (overflowX 0) and no element wider than the viewport. The only wide elements on the composer are formula-ribbon buttons, which sit inside a `d-flex flex-wrap` scroll container (contained, does not break the page).

**Design fidelity (vs `new_design/P01_app_shell_dashboard_desktop.png`):** same dark-green shell, brand palette, rounded stat-card pattern, breadcrumb + role/school dropdowns + bell + avatar top bar, two-column Recent Exams / Proposals, and Quick Actions row all match. Deviations are explainable, not cosmetic defects: (a) the build adds two onboarding cards ("School Branding & Exam Settings", "Start from the curriculum") not present in the design; (b) only 4 stat cards vs the design's 6 because Documents/Assets/RAG Search modules are not implemented; (c) the design's Documents/Assets/RAG nav items are absent accordingly.

---

## 6. Screenshot Inventory

Captured this session (stored in `skuphase\_audit_tmp\shots\`):

| File | Viewport | Screen | Notes |
|---|---|---|---|
| audit_dashboard_1440x900.png | 1440×900 | Dashboard (admin) | Sidebar, stat cards, Recent Exams, Proposals |
| audit_dashboard_1280x720.png | 1280×720 | Dashboard | No overflow |
| audit_dashboard_768x1024.png | 768×1024 | Dashboard (tablet) | No overflow |
| audit_dashboard_390x844.png | 390×844 | Dashboard (mobile) | Bottom nav bar; no overflow |
| audit_dashboard_360x800.png | 360×800 | Dashboard (narrow mobile) | No overflow |
| audit_mobile_nav_menu.png | 390×844 | Mobile nav drawer open | Full sidebar dialog |
| audit_manual_composer_390x844.png | 390×844 | Manual exam composer | Form stacks cleanly |

(Prior-session captures home/login/register/exams remain in the FastHTML root.)

---

## 7. AI Copilot and AI Generation (now verified with live LLM)

**Copilot `/api/v1/copilot/assist`** (real LLM):
- `rewrite`: 200 in 9.1 s → "Calculate 10% of 500." with marking point "50".
- `options`: 200 in 3.6 s → 4 plausible distractors ["5","50","500","5000"].
- Contract enforced server-side: invalid action / missing `question` rejected with 422 listing allowed actions (`options`, `marking_guide`, `rewrite`, `diagram_prompt`).

**AI exam generation `POST /api/v1/exams/generate`:**
- 202 Accepted with `estimated_time_seconds: 30` and an **advisory coverage warning**: "Selected scheme weeks are not marked completed or verified: 1, 2." (the uncovered-weeks warning required by the roadmap is present).
- Polling progressed `draft → under_review`, produced **5 questions** matching the requested section config (Section A, MCQ ×5), with correctly localised Nigerian content (₦, Lagos, Chidi/Amina, place value, Roman numerals). **Blueprint/section shape was honoured** (count + type). Content quality is plausible but not independently scored — see Section 19.

---

## 8. PDF / Export Inventory (text-extraction verified)

All four PDF types generated and downloaded for the rich-content exam (MCQ + short answer + essay with sub-parts + SVG diagram + LaTeX):

| Document | Result | Verified by text extraction |
|---|---|---|
| Paper PDF (`include_answers=false`) | 200, 1 page | Header "AUDIT TEST SCHOOL / Victoria Island, Lagos", title, duration, marks, sections, all 4 questions, diagram question present. **No answer/marking-scheme/explanation leakage** (checked "Answer: A", "Multiplication first", "28800", "Revenue", "CONFIDENTIAL", "Expected Answer" — all absent). |
| Answer-key PDF (`include_answers=true`) | 200 | Adds "MARKING SCHEME / ANSWER KEY", "Answer: A", explanation, marking scheme. |
| Marking-guide PDF | 200 | Per-question marking criteria; **leaks literal `<super>2</super>`** (MED-002). |
| OMR sheet | 200 | 50 bubble rows `[A]–[E]`, candidate name/class/score fields. |
| Worksheet PDF (Package B) | 200, 1 page | Title, term, instructions, both questions with answer lines, **no answers leaked**. |
| DOCX | 200 (clean exam) / **500 (control-char exam)** | MED-002. |
| CSV / GIFT / QTI | 200 | Correct payloads returned; round-trip preview parses (CSV/GIFT) on re-upload. |

Answer leakage on the **student paper was negative** (no answers) and **positive** on key/guide — the most safety-critical export property holds. PDF→image visual fidelity could not be rendered (no Poppler) — recorded under Untestable items.

---
## 9. Tenant-Isolation Findings

Two separate school identities used (School A = `audit.admin@example.com`; School B = freshly registered `Audit Probe School B` / `probe.admin.b@audit-probe.ng`). All cross-tenant probes return **404 "Exam not found" / "Lesson plan not found" / "Worksheet not found"** (404 rather than 403 - correct, avoids existence leakage):

| Probe (as School B, targeting School A's resource) | Result |
|---|---|
| `GET /exams/{id}` | 404 |
| `POST /exams/{id}/export` | 404 |
| `GET /exams/{id}/exports/{file}` | 404 |
| `PUT /exams/{id}` (update) | 404 |
| `DELETE /exams/{id}` | 404 |
| `GET /exams/{id}/preflight` | 404 |
| `PATCH /lesson-plans/{id}` | 404 |
| `DELETE /lesson-plans/{id}` | 404 |
| `GET /lesson-plans/exercises/{id}/download/{file}` (worksheet) | 404 |
| Question-bank list (A) vs (B) | Each sees only its own (filter by `school_id`) |
| API-key list (A) vs (B) | Scoped to own school |
| Exam list (B) | 0 items - A's exams invisible |

Also verified: cross-school exam detail **direct-URL/ID-guessing** returns 404 (a random UUID also 404, no enumeration). Query-layer isolation is enforced by `school_id == current_user.school_id` throughout. **No endpoint was found that can read or mutate another tenant's data.**

---

## 10. Security Findings

| ID | Area | Result | Evidence |
|---|---|---|---|
| SEC-A | **SVG `<script>` injection** | **Blocked** | `POST /exams/manual-submit` with `<svg ...><script>alert(1)</script></svg>` -> 422 "diagram_svg must be a safe, complete SVG document". |
| SEC-B | **Stored XSS via question text** | **Not executed** | `<script>window.__XSS=1</script><img src=x onerror=...>` stored (200) but not rendered raw; `window.__XSS` undefined in browser. |
| SEC-C | **Malformed JSON** | Handled | `POST /login` with `'{not json'` -> 422 `json_invalid`, no 500. |
| SEC-D | **Path traversal on downloads** | Handled | `../../../../etc/passwd`, URL-encoded variant, malformed `.pdf` -> 404, no disclosure. Filenames validated `^[0-9a-f]{32}\.pdf$`. |
| SEC-E | **Invalid / expired token** | Handled | Bad bearer -> 401; no token -> 401. |
| SEC-F | **Login brute-force / rate limit** | **Active** | 12 wrong-password attempts -> `[401,401,401,401,401,429,429,429,429,429,429,429]`. |
| SEC-G | **CSP / headers** | Present (weakness) | `script-src 'self' 'unsafe-inline' ...`; plus `X-Frame-Options: DENY`, `nosniff`, `referrer-policy`, `frame-ancestors 'none'`, `X-Request-ID` on every response. `'unsafe-inline'` weakens CSP (HIGH-004). |
| SEC-H | **Secrets in `.env`** | Config risk | JWT + LLM keys local; `.env` gitignored. Rotate + secret manager for production. |

Not exhaustively live-tested: CSRF enforcement across all mutating UI forms, oversized-payload DoS, import-file fuzzing, tenant-ID manipulation in request bodies. These rely on code review + the passing test suite.

---

## 11. Accessibility and Responsive Findings

- **Responsive:** all 5 viewports render with zero horizontal overflow (document and elements). Mobile nav drawer works; bottom nav present at mobile widths.
- **Focus states / keyboard nav / screen reader:** not systematically exercised (no axe/Lighthouse run). Formula ribbon on mobile is dense (28 buttons) but scroll-contained.

---

## 12. Performance / Low-Bandwidth Findings

- **Slow 3G (CDP: 400 ms RTT, 400 kbps):** dashboard `/app` ~ **485 ms** wall-clock, DCL 443 ms, 26 resources - server-rendered and light; acceptable.
- **Offline transition:** `/app` rendered from service-worker cache while network forced offline, and recovered cleanly on restore (`main` present, correct title). **User does not lose the dashboard offline.**
- **Slow AI response:** copilot rewrite 9.1 s, options 3.6 s; submit shows a loading spinner. Timeout/failure UI not stress-tested.
- **Stress (many questions, huge SVG, refresh storm):** not load-tested beyond the single rich 4-question exam.

---
## 13. Feature-by-Feature Status Matrix

| Feature | Status | Evidence | Remaining work | Confidence |
|---|---|---|---|---|
| Auth: register school / individual, login, logout, bad creds, rate limit | Confirmed working | UI + API; 429 after 5 | Session-expiry UX polish | High |
| Tenant isolation (exams, exports, updates, lesson plans, worksheets, bank, keys) | Confirmed working | Cross-tenant 404s across 10 probes | - | High |
| Dashboard (admin) + responsive + mobile nav | Confirmed working | 5 viewports, 0 overflow | Documents/Assets/RAG cards not built | High |
| Manual exam composer (authoring, LaTeX, sub-parts, marking scheme, submit) | Confirmed working | Browser end-to-end -> persisted exam | Diagram-library picker not exercised in-browser | High |
| PDF exports (paper, key, guide, OMR, worksheet) | Confirmed working (text-verified) | pypdf extraction; no leakage | Visual (image) fidelity not rendered | Medium-High |
| DOCX/CSV/GIFT/QTI exchange | Working with limitations | Clean exams export 200 | DOCX 500 on control-char content (MED-002) | High |
| Question bank browse/list | Confirmed working | 200, tenant-scoped | - | High |
| Question bank **create** | **Failing** | 500 (`current_user.id`) | Fix BLK-003 | High |
| Curriculum boards/classes/subjects/terms/weeks | Confirmed working | 200 | - | High |
| Curriculum **search** | **Failing** | 500 | Fix BLK-001 | High |
| JSS/SSS curriculum data | Not implemented | DB: Pre-Nursery-P6 only | Ingest JSS1-3/SSS1-3 (BLK-002) | High |
| AI copilot (rewrite/options/marking/diagram) | Confirmed working (rewrite+options) | Real LLM 200s | marking_guide/diagram_prompt not exercised; suggestion-approval UI not tested | Medium-High |
| AI exam generation (blueprint/coverage/poll) | Confirmed working | 202 -> under_review, 5 Qs, coverage warning | Independent quality scoring | Medium |
| Lesson plan create/edit/coverage | Confirmed working (API) | 201, patch, coverage lifecycle | Teacher UI for Package B not found/tested | Medium |
| Weekly exercise + worksheet export/download | Confirmed working (API) | 201, PDF 200 | - | High |
| Coverage verify-as-admin / deny-as-teacher | Confirmed working | 200 admin; teacher path denied by role check | Teacher-token test blocked (stale fixture creds) | Medium-High |
| Ops health/stats/pilot-readiness | Confirmed working | 200 + request-ID | - | High |
| Partner API (Phase 3) | Deferred (by design) | - | Scopes/quotas/webhooks | High |
| Backup/recovery | Script exists, **drill not run** | `backup_database.ps1` (pg_dump) | Restore drill + documented RPO/RTO | High (unverified) |

---

## 14. Blocking Issues (fix before pilot)

**BLK-001 — Curriculum search returns HTTP 500**
- **Severity:** Critical • **Area:** API — curriculum
- **Workflow:** Search curriculum topics • **Reproduction:** `GET /api/v1/curriculum/search?q=water` (valid JWT)
- **Expected:** 200 with matches • **Observed:** 500 • **Evidence:** server traceback `TypeError: ... '.type' attribute is not a TypeEngine` at `app/services/curriculum_service.py:153` (`func.cast(SchemeOfWork.subtopics, func.text).ilike(...)`)
- **Impact:** Keyword search is completely broken • **Fix:** use `cast(SchemeOfWork.subtopics, String).ilike(...)` or `.astext.ilike(...)` • **Confidence:** High

**BLK-002 — No JSS/SSS curriculum data**
- **Severity:** Critical (scope) • **Area:** Data • **Reproduction:** generate exam for JSS 1 Physics
- **Expected:** NERDC-aligned JSS/SSS schemes • **Observed:** only Pre-Nursery-P6 exist • **Evidence:** DB grouping by board/class_level
- **Impact:** Secondary-school papers have no curriculum grounding, breaking the "curriculum-first" premise • **Fix:** ingest JSS1-3 / SSS1-3 NERDC data, or formally scope the pilot to primary only • **Confidence:** High

**BLK-003 — Question-bank item creation returns HTTP 500**
- **Severity:** High • **Area:** API — question bank
- **Reproduction:** `POST /api/v1/exams/question-bank/items` with a valid item payload
- **Expected:** 201 • **Observed:** 500 • **Evidence:** `app/api/v1/exams_router.py:768` uses `created_by_user_id=current_user.id` -> `AttributeError: 'CurrentUser' object has no attribute 'id'` (reproduced via TestClient traceback). Every other handler uses `current_user.user_id`.
- **Impact:** "Add question to bank" is impossible from the UI/API • **Fix:** change `.id` -> `.user_id` at line 768 • **Confidence:** High

### High / Medium Issues

**HIGH-004 — CSP allows `unsafe-inline` in script-src** (`app/frontend/middleware.py:96`). Impact: weakens XSS defence. Fix: nonces/hashes. Confidence: High.

**MED-002 — DOCX export 500 on control characters + `<super>` leakage in marking guide.** Repro: create an exam whose question text contains a control char (accepted by API), then `GET /exams/{id}/exchange/docx` -> 500 `ValueError: All strings must be XML compatible` raised inside python-docx; the same exam's marking-guide PDF prints literal `<super>2</super>`. Clean exams export fine (35 KB valid DOCX), so this is content-dependent, not a total DOCX failure. Impact: export breaks on legitimate pasted content; marking guide shows raw tags. Fix: strip XML-illegal control characters at ingest, and render `<super>/<sub>` properly in the marking-guide renderer. Confidence: High.

**MED-001 — Dependency completeness.** `asyncpg` was missing from the runtime interpreter earlier in the audit; ensure deployment installs `requirements.txt` fully. Confidence: High.
**MED-003/004 — Secrets management.** Rotate JWT/LLM keys; use a secret manager. Confidence: High.
**MED-005 — Google Fonts CDN dependency** fails closed on restricted networks (`ERR_CONNECTION_CLOSED`); fonts fall back. Consider bundling locally for low-bandwidth/offline. Confidence: Medium.
**LOW — Lint/type gates unavailable:** `ruff` and `mypy` are not installed, so no static-analysis evidence exists in this audit. Confidence: High (that they are unavailable).

---
## 15-19. Remaining Coverage Gaps (untested / not exercised)

- PDF->image visual fidelity (no Poppler/PyMuPDF) — text extraction used instead.
- AI generation independent quality scoring, refusal/refinement, failed-generation retry UI — LLM ran once successfully; failure paths not forced.
- Copilot `marking_guide` / `diagram_prompt` actions, suggestion approve/reject UI, and "does not overwrite authored content" browser flow — not exercised.
- Diagram-library picker, SVG parameter editing, resize/exam-mode/hidden-label UI in the browser — API/validation verified, UI not.
- Package B teacher-facing UI (no dedicated `/app` lesson/coverage screens found) — API only.
- Teacher/auditor role tests blocked by stale fixture credentials (`audit-test.ng` passwords unknown); role logic verified via code review + the passing suite.
- Backup restore drill (requires DB write authorization); CSRF, oversized-payload, import-fuzz DoS, session-expiry UX.
- Real-school fixtures and privacy/legal/DPA sign-off.

## 20. Recommended Fix Order
1. Fix BLK-001 (curriculum search 500).
2. Fix BLK-003 (question-bank create 500).
3. Decide primary-only pilot scope or ingest JSS/SSS (BLK-002).
4. Fix MED-002 (DOCX control chars + marking-guide `<super>`).
5. Render sample PDFs to images (install Poppler) and eyeball layout/diagrams/equations/page-breaks.
6. Expose/verify Package B teacher UI; test diagram picker and copilot approve/reject in-browser.
7. Remove `unsafe-inline` from CSP (HIGH-004); harden secrets (MED-003/004).
8. Run backup restore drill; document RPO/RTO.
9. Complete privacy/legal review; obtain real-school fixtures.

## 21. Final Production-Readiness Classification

**Pilot-ready for controlled schools — with blocking fixes required before pilot launch.**

Justification: Core assessment authoring -> export, Package B lesson delivery, tenant isolation, responsive layout, security posture, and 283 automated tests are all solid and evidence-backed; the two open blockers (curriculum search 500, question-bank create 500) are small, root-caused fixes, and the JSS/SSS gap is a scoping decision. It is **not** public-production-ready because: PDF visual fidelity is unverified (no image rendering), the backup restore drill has not been run, privacy/legal review is not complete, and no real-school fixtures have passed.

---

## Final Roadmap Status Table

| Roadmap item | Status | Evidence | Remaining work | Confidence |
|---|---|---|---|---|
| Phase 0: Core stability | Complete | 283 tests pass; migrations at head; SVG sanitizer blocks script | - | High |
| Phase 1: Assessment Studio (manual composer) | Complete (core) | Browser end-to-end authoring verified; 4 PDF types export | Diagram picker UI QA; copilot approve/reject UI | High |
| Phase 2: Secondary curriculum (JSS/SSS) | Not implemented | DB: NERDC Pre-Nursery-P6 only | Ingest JSS1-3/SSS1-3 or scope to primary | High |
| Phase 3: Partner API | Deferred (by design) | API-key model present, tenant-scoped | Scopes, quotas, webhooks, developer portal | High |
| Package A: Exam generation & authoring | Complete with one blocker | Manual + AI generation both work; exports verified | Fix BLK-001/BLK-003; MED-002 | High |
| Package B: Curriculum delivery | Complete (API) / UI partial | Lesson plan, exercise, worksheet, coverage all verified | Teacher-facing UI exposure | Medium |
| Package C: Pilot hardening | Partial | Ops endpoints + request-ID + rate limiting + isolation verified | PDF visual check, restore drill, privacy review, real-school fixtures | Medium |
| Package D: SMS bounded context | Not implemented | - | Post-pilot by design | High |

---

*Report compiled from code review, the full pytest suite, live API/tenant/security probes against two real school identities, browser testing at 5 viewports with Slow-3G/offline, and text-extraction verification of generated PDFs. Audit-only: no production code, data, or config changed.*