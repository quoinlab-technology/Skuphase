# SkuPhase Visual and End-to-End Audit Remediation Plan

**Source audits**

- Pass 1: `skuphase_audit_pass1/VISUAL_E2E_AUDIT_PASS_1.md`
- Pass 2: `skuphase_audit_pass2/VISUAL_E2E_AUDIT_PASS_2.md`
- Audit date: 14 October 2026
- Status: **Remediation not started; application not production-ready**

This document consolidates both audits into one implementation path. It is the
working source of truth for fixing the findings and for deciding when the next
visual/E2E audit can be considered a release gate.

The audits were read-only. No source code was changed and no QA data was
deleted. The findings below distinguish confirmed defects, blocked tests,
infrastructure failures, and observations that are valid but not release
blockers.

---

## 1. Executive decision

The core SkuPhase workflows are real and usable:

- authentication, session expiry, logout, and case-insensitive email login;
- starter/guided and advanced exam generation;
- manual exam composition;
- formulas, SVG diagrams, preview, draft rescue, reorder, duplicate, delete,
  validation, and CSV export;
- primary and secondary AI generation;
- lesson-plan creation, AI lesson-note generation, editing, saving, approval,
  and coverage tracking;
- manual worksheet creation and PDF export;
- responsive behavior at 390px and 360px for most tested surfaces;
- loading indicators on the tested slow-network generation path.

The application must not be presented as production-ready until the following
are complete and re-verified:

1. worksheet marks are stored and printed correctly;
2. worksheet PDF identity (subject, class, term) is correct;
3. teaching feedback is displayed and consumed in the correct context;
4. teaching and exam pages remain available under concurrent/slow requests;
5. exam PDF and Word downloads work from a browser session;
6. AI title and focus-topic data survives the entire generation pipeline;
7. dashboard/list status counts and labels agree with detail/API state;
8. lesson notes can be exported/printed;
9. the school-logo failure degrades safely instead of producing broken printed
   documents.

---

## 2. Finding disposition and traceability

### Pass 1 findings

| Finding | Disposition | Implementation area |
|---|---|---|
| P1-F01 Word export HTTP 500 | Confirmed blocker | Shared export foundation |
| P1-F02 PDF download HTTP 401 | Confirmed blocker | Authenticated download proxy |
| P1-F03 title/focus topics lost | Confirmed blocker | AI wizard and exam schema |
| P1-F04 dashboard counters ignore filters | Confirmed blocker | Exam list API/dashboard |
| P1-F05 list pills/badges disagree | Confirmed major | Status normalization |
| P1-F06 AI exam says Manual entry | Confirmed major | Provenance in API/detail |
| P1-F07 quality report shows green 0% | Confirmed major | Quality report semantics |
| P1-F08 CSP `eval` error | Confirmed major | Wizard/client script |
| P1-F09 responsive overflow | Confirmed major | App shell/exam layout CSS |
| P1-F10 Supabase logo 504 | Confirmed major/infrastructure | Logo storage/fallback |
| P1-F11 premature week validation | Confirmed polish | Wizard validation state |
| P1-F12 default document title | Confirmed polish | Page titles |
| P1-F13 authenticated login/no signed-out flash | Confirmed polish | Auth routes |
| P1-F14 fabricated “by Adaeze” attribution | Confirmed data-display defect | Exam row provenance |
| P1-F15 delete has no confirmation | Confirmed polish/safety | Faststrap modal |
| P1-F16 `[1 marks]` pluralization | Confirmed polish | Print formatter |
| P1-F17 wizard step label changes | Confirmed consistency defect | Wizard stepper |

### Pass 2 findings

| Finding | Disposition | Implementation area |
|---|---|---|
| P2-F01 worksheet marks hardcoded to 1 | Confirmed blocker | Worksheet data model/export |
| P2-F02 worksheet header wrong | Confirmed blocker | Worksheet metadata/export |
| P2-F03 duplicate submission | **Withdrawn** | Do not implement as a confirmed defect |
| P2-F04 teaching flashes discarded/leaked | Confirmed blocker | Teaching shell feedback |
| P2-F05 teaching 500/504 under load | Confirmed blocker | Teaching aggregation/reliability |
| P2-F06 regeneration destroys edits | Confirmed major | Unsaved-change guard |
| P2-F07 lesson notes cannot export/print | Confirmed major | Lesson-note exchange |
| P2-F08 exam downloads unavailable from browser | Confirmed carry-over blocker | Shared export foundation |
| P2-F09 school logo 504 | Confirmed major/infrastructure | Logo storage/fallback |
| P2-F10 exams list overflows at 1024px | Confirmed major | Table/container CSS |
| P2-F11 scheme topics truncated | Confirmed polish | Week selector |
| P2-F12 worksheet form lacks marks/type/key | Confirmed feature gap | Worksheet authoring |
| P2-F13 default document title | Carry-over of P1-F12 | Page titles |
| P2-F14 coverage banner provenance unclear | Confirmed UX issue | Coverage/flash semantics |
| P2-F15 teaching accessibility issues | Confirmed polish | Form semantics/touch targets |
| P2-F16 subject list not re-anchored on class change | Confirmed polish | Scope selector state |

P1-F01/P1-F02 remain open as P2-F08. P1-F09 and P1-F10 are corroborated by
Pass 2. P1-F12 remains open as P2-F13. P2-F03 is explicitly withdrawn because
the two rows were created by two separate audit runs, not one duplicate click.

---

## 3. Implementation principles

1. **Preserve working workflows.** Fix the data and transport boundaries before
   redesigning pages.
2. **One source of truth per concept.** Status, title, subject, class, term,
   marks, provenance, and feedback must each have one canonical representation.
3. **Browser sessions must never be forced to hand Bearer tokens to download
   links.** Frontend routes should authenticate in-process and stream the file.
4. **A document must fail safely.** Missing optional branding cannot invalidate
   an otherwise correct PDF or Word document.
5. **Never silently discard teacher input.** Persist or explicitly warn before
   replacing it.
6. **Do not use a cosmetic value to represent an unknown value.** For example,
   an uncomputed quality report is not a green `0%` score.
7. **Use Faststrap UI primitives** for confirmation, validation, loading, and
   feedback states; do not introduce native alerts for these flows.
8. **Every fix gets a regression test and, where visual, a screenshot at 1440,
   1024, 390, and 360px.**

---

## 4. Phase 0 — Baseline, data safety, and dependency inventory

### 4.1 Freeze the audit evidence

- Keep both audit directories outside the application runtime paths.
- Record the current commit before edits.
- Do not edit the audit evidence or overwrite screenshots.
- Create a remediation branch/commit before implementation.

### 4.2 Inventory production dependencies

- Confirm the dependency file used by deployment (`requirements.txt`,
  `pyproject.toml`, or equivalent).
- Add a pinned compatible `python-docx` version.
- Confirm PDF dependencies and fonts are available in the deployment image.
- Build a clean environment and run the export tests there; the local machine
  having a package installed is not sufficient.

### 4.3 QA data cleanup plan

The audits retained test data. Create a targeted, reviewed cleanup script that
accepts explicit IDs and prints a dry-run list before deletion. The first
cleanup set includes:

- Pass 2 lesson plan `4cb87abc-1854-45b9-a14d-32d9fb9be4d3`;
- Pass 2 worksheet `a4681798-7783-4a7e-99c1-98833e71a64e`;
- withdrawn-harness worksheet `56998394-7824-4b7f-86af-bce7d1278c1f`;
- its coverage row;
- the four Pass 1 QA exam IDs listed in the Pass 1 report;
- abandoned test sessions containing only the documented QA labels.

Do not run a broad status-based delete. Run the cleanup only after the owner
confirms the IDs and export evidence is retained.

### Phase 0 acceptance

- Clean environment installs all export dependencies.
- Baseline test command and current failures are recorded.
- QA cleanup is explicit, reviewable, and reversible where possible.

---

## 5. Phase 1 — Shared export and authenticated-download foundation

This phase fixes P1-F01, P1-F02, P2-F07, and P2-F08 together because they share
the export boundary.

### 5.1 Word export

Files to inspect:

- `app/services/question_exchange.py`
- `app/api/v1/exams_router.py`
- deployment dependency files
- export tests

Implementation:

- Add/pin `python-docx`.
- Keep the import inside the exporter if desired, but catch missing dependency
  and return a structured application error rather than an unhandled 500.
- Ensure the frontend renders a Faststrap error state for export failure rather
  than replacing the document with a generic error page.
- Test exam Word exports for manual and AI exams.
- Test worksheet and lesson-note Word exports once those routes exist.

### 5.2 PDF/browser download proxy

Implementation:

- Add an authenticated frontend route such as
  `/app/exams/{exam_id}/exports/{filename}`.
- Read the signed session cookie, call the API through `call_api()` with the
  Bearer header, and stream the upstream bytes with the correct content type and
  `Content-Disposition`.
- Keep the API endpoint Bearer-protected.
- Update the UI to target the frontend route, never the raw API URL.
- Handle upstream 401/403/404/500 with a branded Faststrap message and no token
  leakage.
- Use the same pattern for lesson-note and worksheet exports.

### 5.3 Export contract tests

Add tests for:

- authenticated PDF download;
- unauthenticated download rejection;
- Word attachment content type and filename;
- expired session redirect;
- missing export file;
- malformed export response;
- large-file streaming without loading unnecessary copies into memory.

### Phase 1 acceptance

- PDF, DOCX, CSV, GIFT, and QTI downloads work from a normal browser session.
- No raw API JSON is shown to users for a valid export click.
- No access token appears in a URL, HTML, screenshot, or log.
- Export tests pass in a clean deployment environment.

---

## 6. Phase 2 — Exam generation data and status integrity

This phase fixes P1-F03, P1-F04, P1-F05, P1-F06, P1-F07, P1-F14, and P1-F17.

### 6.1 Canonical exam metadata

Add or confirm fields for:

- custom title;
- focus topics;
- custom AI instructions;
- selected curriculum weeks;
- source/provenance (`manual` vs `ai_generated`);
- workflow state/status.

If title/focus data is stored in a JSON configuration field, document and test
that contract. If relational columns are required, add an Alembic migration.
Do not create parallel fields with ambiguous precedence.

Update the full path:

`wizard state → frontend payload → request schema → job payload → generator →
exam persistence → list API → detail API → print/export metadata`.

### 6.2 Title and focus-topic acceptance

- Enter a distinctive title and focus topic in the wizard.
- Confirm them on the summary.
- Confirm them in the request/job payload.
- Confirm them through the API detail response.
- Confirm them in list/detail pages and exported documents.
- Confirm fallback behavior when no custom title is supplied.

### 6.3 Canonical workflow-state resolver

Create one shared resolver for API responses, dashboard counters, list pills,
row badges, and detail badges. It must map internal states such as
`teacher_review`, `final_submitted_by_teacher`, `generation_requested`,
`approved`, `failed`, and `draft` into stable UI states.

Implementation:

- Make `workflow_state` a supported API filter, or consistently translate the
  UI filter into the supported API parameter.
- Include the canonical workflow state in list and detail responses.
- Add `under_review` and `pending_review` to badge labels.
- Calculate counts from the same filtered dataset/resolver used by rows.
- Ensure pills partition the complete list without silently dropping states.
- Replace fabricated author text such as “by Adaeze” with the real creator name,
  or show a neutral value when unavailable.

### 6.4 Provenance and quality report

- Return `source_type`/`ai_generated`/generation provenance from the API.
- Resolve the detail origin chip from that canonical value.
- Distinguish `not scored`, `pending`, and numeric score `0`.
- Compute a documented weighted overall score from dimension scores, or show a
  neutral “Not yet scored” state until a report exists.
- Ensure color treatment does not imply success for an unknown score.

### 6.5 Wizard consistency

- Keep the stepper label stable (`Curriculum` or `Sources`, not both).
- Do not show week validation before the user attempts to continue.
- Replace eval/new-Function behavior causing the CSP error with direct parsing or
  a safe, CSP-compatible implementation.

### Phase 2 acceptance

- Dashboard, list, row, detail, and API show the same state for the same exam.
- Custom title/focus data survives generation.
- Manual and AI provenance chips are correct.
- Quality report never presents an unknown score as a healthy zero.
- No CSP/page errors appear during the wizard.

---

## 7. Phase 3 — Teaching and worksheet correctness

This phase fixes P2-F01, P2-F02, P2-F04, P2-F06, P2-F07, P2-F12, P2-F14,
P2-F15, and P2-F16.

### 7.1 Worksheet question model and marks

The current one-question-per-line input is insufficient for reliable marking.
Implement a backward-compatible structured question representation:

- question text;
- question type;
- marks;
- answer key/answer options where applicable;
- optional explanation or teacher note.

For legacy plain text, support an explicit suffix such as `[5 marks]` using a
strict parser and default to one mark only when no suffix exists. Do not append a
second suffix when one is already present.

Prefer an explicit per-question marks control in the authoring UI. Persist the
structured values through the API and database/JSON field. Add a migration only
if the current storage cannot represent them safely.

Update:

- creation schema and route;
- worksheet model/storage;
- preview;
- PDF export;
- marking guide/marksheet;
- grading calculations;
- CSV or exchange output where applicable.

### 7.2 Worksheet metadata

Carry `subject`, `class_level`, and `term` through creation. If a worksheet is
linked to a lesson plan, resolve missing metadata from that plan consistently.
The PDF header must display:

- subject as subject;
- class/grade as class;
- term as term;
- custom title when provided.

Test Primary and Secondary examples.

### 7.3 Teaching feedback

- Pass `flash=pop_flash(req)` into the Teaching `AppShell`.
- Ensure every `push_flash` is consumed exactly once.
- Prevent stale messages from leaking to Dashboard or Exams.
- Keep coverage warnings separate from action-result flashes and label their
  provenance.
- Add success/error tests for plan creation, AI note generation, save, approve,
  coverage, and worksheet creation.

### 7.4 Unsaved lesson-note protection

- Track dirty state in the note editor.
- Before regeneration or guidance-chip replacement, show a Faststrap modal.
- Offer “Cancel” and “Replace my draft”.
- Preserve the existing draft when cancelled.
- Where appropriate, offer “build on this draft” instead of replacement.

### 7.5 Lesson-note export

Add approved lesson-note PDF and Word export using the shared authenticated
download foundation. Preserve:

- headings and lists;
- formulas/KaTeX content;
- diagrams/SVG where supported;
- tables;
- school logo fallback;
- class, subject, term, week, and teacher metadata.

### 7.6 Worksheet authoring accessibility

- Add marks, question type, and answer-key controls.
- Replace ambiguous shared-form submit buttons with clearly labelled actions.
- Add `aria-describedby`, word/character guidance, and visible labels.
- Make refinement chips distinguishable from Save/Approve submits.
- Bring touch targets to approximately 44px minimum.
- Preserve keyboard focus after redirects or modal closure.

### 7.7 Class/subject scope safety

- On class change, re-fetch available subjects.
- Clear an invalid previous subject selection.
- Show a concise hint that the subject list is class-scoped.
- Keep server-side validation authoritative.

### Phase 3 acceptance

- Mixed-mark worksheets produce correct previews, PDFs, marksheets, and grading.
- Worksheet headers identify the correct subject, class, and term.
- Every Teaching action gives immediate contextual feedback.
- Regeneration cannot silently destroy edits.
- Lesson notes are printable/exportable.
- Teaching controls are accessible and usable on narrow mobile screens.

---

## 8. Phase 4 — Reliability, branding, and responsive hardening

This phase fixes P1-F09/P1-F10 and P2-F05/P2-F09/P2-F10, plus the remaining
blocked reliability checks.

### 8.1 Teaching workspace reliability

Instrument each upstream call in `/app/teaching` with:

- request name;
- elapsed time;
- status code;
- timeout/failure category;
- correlation/request ID.

Then:

- parallelize independent calls with bounded `asyncio.gather` tasks;
- apply explicit per-call timeouts;
- isolate failures so one unavailable source renders an inline partial-state
  message instead of failing the whole page;
- avoid unbounded remote calls during a page render;
- confirm database pool sizing and worker behavior under concurrent generation.

Reproduce with serial, concurrent, and slow-3G runs before declaring fixed.

### 8.2 Logo storage and fallback

Investigate the Supabase object itself, bucket policy, CDN response, object
path, and upload metadata. Then:

- keep a local/default SkuPhase mark available;
- add image fallback behavior in authenticated pages and print templates;
- use a bounded timeout for remote logo fetches;
- do not block document generation on a remote logo;
- optionally cache a verified logo locally for document rendering;
- record a warning, not a fatal exception, when the logo is unavailable.

Test valid logo, missing object, 404, 504, and slow response.

### 8.3 Responsive overflow

- Move `.app-table-container { overflow-x: auto; }` to the base rule.
- Keep vertical clipping/scrolling intentional.
- Reduce or collapse topbar user/school controls below approximately 400px.
- Test 1024px exams list, 1024px detail, 360px detail, and the clean 390px
  baseline.
- Ensure local table scrolling does not widen the document.

### Phase 4 acceptance

- `/app/teaching` remains usable under concurrent and slow requests.
- No page-level overflow at 1440, 1024, 390, or 360px except intentional local
  tab/table scrolling.
- Printed documents always contain a valid logo or a clean fallback.
- Supabase logo failure cannot produce a 500/504 document failure.

---

## 9. Phase 5 — Remaining visual and content polish

These are not the first release blockers but must be closed before declaring the
audit complete.

- Add per-route `Title(...)` values so `document.title` is never “FastHTML page”.
- Prevent an already-authenticated user from seeing the login page, or show a
  clear “Continue to workspace” path.
- Add a signed-out confirmation flash where the user can actually see it.
- Add full topic tooltips/accessible expansion in the week selector.
- Confirm the manual-question delete action with a Faststrap modal.
- Correct singular/plural marks (`1 mark`, `2 marks`) everywhere, including PDFs.
- Keep wizard labels stable before and after generation.
- Review focus rings, contrast, touch targets, screen-reader names, and keyboard
  behavior on all new Teaching controls.
- Add visible long-title handling and test titles long enough to wrap/truncate.
- Confirm no raw provider messages, tracebacks, or secrets reach the UI.

### Phase 5 acceptance

- All P1/P2 visual findings are either fixed or explicitly accepted with a
  documented reason.
- Accessibility and title checks pass at all four required viewport sizes.

---

## 10. Phase 6 — Blocked scenario completion

After Phases 1–4, repeat the scenarios previously blocked by defects or test
constraints:

1. AI provider failure and retry.
2. Empty curriculum response.
3. PDF layout and page-break QA.
4. Word export for exams, worksheets, and lesson notes.
5. Long-title display and export.
6. Mermaid/diagram rendering where the workflow claims support.
7. Full approval chain beyond one-step approve.
8. OMR generation and grading logic.
9. Slow-network worksheet and lesson-note exports.
10. Refresh/navigation during each background generation job.

Each scenario must have a reproducible setup, expected outcome, screenshot or
machine-readable evidence, and cleanup record.

---

## 11. Test and evidence plan

### Automated tests

Add or update tests for:

- request schemas and title/focus persistence;
- status filtering and count partitioning;
- provenance and quality-score semantics;
- worksheet marks parsing and grading;
- worksheet metadata mapping;
- flash consumption;
- export content types, auth, and failure responses;
- logo fallback;
- session expiry and platform/public redirect selection;
- CSP-safe wizard scripts;
- lesson-note dirty-state behavior where testable.

### Browser verification

Use Playwright at:

- 1440 × 900;
- 1024 × 768;
- 390 × 844;
- 360 × 800.

Repeat under slow 3G for login, generation, save, and export. Capture:

- screenshots for each fixed finding;
- console/page errors;
- failed network responses;
- exact request payloads for wizard data;
- downloaded filenames/content types;
- `scrollWidth` versus `clientWidth`;
- visible loading and modal states.

### Data discipline

- Prefix all audit-created records with `QA-AUDIT-`.
- Keep an ID ledger.
- Clean only explicit IDs after evidence is archived.
- Never use production school records as test fixtures without approval.

---

## 12. Release gate

SkuPhase can leave this remediation cycle only when:

- all High/blocker findings are closed and regression-tested;
- no known export path returns an unexplained 401/500;
- worksheet marks and identity are correct in stored data and printed output;
- Teaching feedback is contextual and does not leak;
- concurrent teaching-page requests complete or degrade gracefully;
- logo failures fall back safely;
- the four viewport sizes have no unintended page overflow;
- all previously blocked scenarios are either passed or explicitly documented as
  out of scope;
- a fresh Pass 3 audit confirms the fixes without source modifications during
  testing;
- QA data cleanup is complete or explicitly approved for retention.

The final report should include a finding-by-finding closure matrix linking each
finding to its commit, test, screenshot, and deployment verification.

---

## 13. Recommended implementation sequence

For efficient delivery, implement in these complete slices:

### Slice 1 — Export foundation

P1-F01, P1-F02/P2-F08, P2-F07, dependency verification, export tests.

### Slice 2 — Exam data/status integrity

P1-F03, P1-F04, P1-F05, P1-F06, P1-F07, P1-F14, P1-F17, CSP fix.

### Slice 3 — Teaching correctness

P2-F01, P2-F02, P2-F04, P2-F06, P2-F12, P2-F14, P2-F15, P2-F16.

### Slice 4 — Reliability and visual hardening

P2-F05, P1/P2 logo findings, P1-F09/P2-F10 overflow, timeout and fallback
instrumentation.

### Slice 5 — Polish and blocked-scenario verification

P1-F11–F17 remaining polish, accessibility, failure-path tests, OMR/approval,
long-title and print verification, then Pass 3 audit.

This sequence keeps correctness and teacher-facing documents ahead of cosmetic
work while ensuring no audit finding is lost.
