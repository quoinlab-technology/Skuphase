# SkuPhase Visual and End-to-End Audit Remediation Plan

**Source audits**

- Pass 1: `skuphase_audit_pass1/VISUAL_E2E_AUDIT_PASS_1.md`
- Pass 2: `skuphase_audit_pass2/VISUAL_E2E_AUDIT_PASS_2.md`
- Audit date: 14 October 2026
- Status: **Local remediation and regression audit substantially complete; external release gates remain open**

This document consolidates both audits into one implementation path. It is the
working source of truth for fixing the findings and for deciding when the next
visual/E2E audit can be considered a release gate.

The audits were read-only. No source code was changed and no QA data was
deleted. The findings below distinguish confirmed defects, blocked tests,
infrastructure failures, and observations that are valid but not release
blockers.

## Implementation progress (14 October 2026)

Phase 1 and Phase 2 are underway. Phase 1's initial code slice now pins the DOCX dependency in both
deployment manifests, routes exam PDF and exchange downloads through the signed
browser session, removes the duplicate local-filesystem PDF handler, and adds a
tenant-checked printable PDF export for saved lesson notes. The worksheet
export already used an authenticated frontend proxy and remains in place. The
teaching workspace now consumes its flash message so export feedback can be
shown in the correct request. Phase 1 remains open until export contract checks
and deployment-environment verification are complete.

Phase 2's first implementation slice persists AI exam title, term, focus topics,
custom instructions, selected curriculum weeks, and authoring provenance; carries
those fields through the generation job, exam responses, list, and paper header;
supports canonical workflow-state filtering and school-scoped status counts; and
adds server-side search across title, subject, and grade so returned rows and
counts share the same query. Permanent generation failures now persist a failed
workflow state, and quality views distinguish an unscored exam from a real zero
score. Remaining Phase 2 acceptance checks include browser/CSP verification,
quality-response contract verification, deployed migration validation, and a
full title/focus round trip in the live workflow. Do not mark either phase
complete until those checks pass.

Phase 3's first linked worksheet slice now parses each line's optional
`[N mark(s)]` suffix instead of forcing every teacher-entered item to one mark,
validates and persists normalized question data in the existing JSON field, and
keeps legacy `text` inputs readable. Worksheet cards show the calculated total;
PDF exports resolve subject and class from the linked curriculum, show the
lesson plan's term and total marks, and avoid printing a second mark suffix.
Answer-space counts are bounded for legacy and new records. This did not require
a database migration because `weekly_exercises.questions` is already JSON.
The change has a direct representative-PDF content check; visual page rendering
is still pending because no local PDF rasterizer is installed. Phase 3 also has
local implementations for unsaved-note protection, lesson-note exports, scope
safety, worksheet accessibility, and coverage provenance; browser/mobile and
deployed end-to-end acceptance remain open.

Phase 3 follow-up slice (14 October 2026): refinement/regeneration now checks
the note editor against its original value and presents a Faststrap-styled
Cancel/Replace modal before sending a request that would discard edits. The
worksheet authoring form supports up to 20 removable question rows with type,
marks, answer options, and staff-only answer keys; MCQ option counts are
validated, options print on the learner PDF, and answer keys remain excluded
from that export. Full scheme topics are available in an accessible expandable
list, class-invalid subjects produce a visible reset notice, and coverage
figures/warnings now explicitly describe the school-wide denominator and
staff/admin responsibilities. Refinement controls have descriptive accessible
names, helper text and mobile touch sizing. Regression tests cover rendering,
scope reset messaging, structured question submission/schema validation, and
PDF option/key separation. No migration was required. The subsequent mobile
browser pass confirmed the dirty-draft modal, focus return, cancel-state
restoration, 44px actions, and no horizontal overflow at 390px; 360px keyboard
and assistive-technology acceptance remains open.

Latest verification update (14 October 2026): the live database reports
`0024_exam_metadata_integrity (head)`, confirming the migration is applied.
The export foundation now includes editable DOCX export for saved lesson notes,
with an authenticated same-origin frontend proxy, tenant-scoped API lookup,
school/class/term/week/teacher metadata, and conversion of headings, lists, and
simple Markdown tables. A new in-memory DOCX structure/content test passes.
The exam-export regression assertion now requires the authenticated same-origin
download URL and rejects direct CDN links. Focused remediation tests passed
after that contract correction. The subsequent authenticated browser pass
returned valid lesson-note PDF and DOCX downloads (200 with expected MIME types
and attachment filenames) after the declared DOCX dependency was installed in
the local test virtualenv. Pagination and rendered document layout remain
unverified; no live school rows were created or changed.

Phase 4 reliability slice (14 October 2026): the Teaching workspace now resolves
scope first, then concurrently fetches its four independent plan/coverage/
worksheet sources. Each read has a five-second timeout, logs a source/category
without logging response bodies, preserves session-expiry redirects, and
degrades to an explicit warning/unknown metric instead of presenting an API
failure as an empty workspace. Regression tests verify overlapping requests and
a timed-out source alongside successfully rendered plan data. This closes the
Teaching-workspace portion of P2-F05 locally; the separate exam-detail 504 seen
in the audit and live slow/concurrent deployment verification remain open.

Phase 4 follow-up slice (14 October 2026): exam fetches now have a 12-second
bound, structured latency/status logging, safe transient-error copy, and a
retry path for the exam page and all three print views; expired-session
redirects still propagate unchanged. School-logo failures now fall back to a
bundled SkuPhase mark in settings, browser exam/print views, and PDF generation;
remote PDF logo fetches are bounded to four seconds, and print auto-open waits
briefly for the local fallback. The exam table now scrolls within its own
container at intermediate widths, with flex-shell width constraints and a
narrow-phone topbar adjustment. These changes are locally regression-tested.
Teaching and the exam list were measured at 1440/1024/390/360 with no document
overflow; exam-detail measurements at those widths, live Storage object/CDN
health, and a deployed concurrent exam-detail run remain release checks.

Browser verification slice (14 October 2026): the authenticated Teaching page
was visually checked at 1440, 1024, 390, and 360 CSS pixels; document
scroll-width matched viewport width at each size. Worksheet question add/remove
works without submitting data, and the dirty-note confirmation was checked at
390px: Keep editing preserved the draft and prevented a refinement request. A
Primary-to-SSS scope change reset an unavailable subject to a valid secondary
subject and displayed the scope warning. This pass exposed Faststrap buttons
that combined its implicit `btn-primary` with outline classes; explicit outline
variants now preserve the brand style and contrast.

Manual-composer follow-up (14 October 2026): mobile browser testing confirmed
the new question-deletion confirmation keeps the card intact when cancelled,
removes only the selected card after explicit confirmation, closes the modal,
and leaves the required final question in place.

Shared-shell title and login follow-up (14 October 2026): `PublicShell`,
`AuthShell`, and `AppShell` now extract page titles into FastHTML's `<head>`;
pages without an explicit title receive a branded default instead of
`FastHTML page`. The public login page redirects an already-authenticated
session to the workspace and consumes the one-shot signed-out flash. Regression
tests cover public/auth/workspace title placement, login redirect, logout flash
consumption, outline-button variants, and the Teaching page title.

Final local-browser follow-up (14 October 2026): verified lesson-note PDF and
DOCX download responses (200, expected MIME type and attachment filename),
then fixed an uncovered API regression where exam-list search referenced an
undeclared query parameter and made the whole list fail. The API now declares
and validates `search`; a router regression test confirms title/subject/grade
filters, and browser search for Physics returns only matching rows. Exam-list
layout was measured at 1440/1024/390/360 with no document overflow; at 1024
the table scrolls within its own region, and keyboard ArrowRight moves that
region horizontally. Mobile cards truncate long titles without displacing the
menu control. This is local acceptance only; deployed verification remains
open.

Final verification slice (14 October 2026): the audited exam-detail page was
opened in the authenticated browser after fixing a null-term crash in its
header; the student paper, answer key, and OMR views now use safe term fallback
text and document-specific titles. The student print view rendered its bundled
brand fallback when the remote school-logo request failed. Exam-detail layout
was measured at 1440/1024/390/360 with no document overflow. The Step 2 wizard
was tested at 390px: empty week selection remains on Step 2 with a visible
warning and a reset Next button; selecting a week advances to Step 3. This
exposed and fixed a malformed flash call that previously returned HTTP 500.
The HTMX guard now uses a registered event listener rather than inline
`hx-on`; the Question Bank delete modal was converted too. Invalid and valid
wizard submissions produced zero browser console errors after this change.
The route-title sweep now covers Start, Curriculum, Administration, Teaching,
Exams, Feedback, exam detail, and the student print view. The complete test
suite, compileall, and whitespace checks passed. Remote Storage 504s,
deployed-only load behavior, and rendered Word/PDF pagination remain external
or human-review gates; local completion does not certify production readiness.

Document verification follow-up (14 October 2026): read-only browser exports
of the retained QA worksheet returned HTTP 200; PDF text confirms the stored
question marks total 37, correct Mathematics/SSS 3/First Term metadata, and no
answer-key leakage. A rendered one-page sample showed legible question spacing
and answer lines. The saved lesson-note PDF and DOCX also returned HTTP 200;
the two-page PDF was rendered and visually inspected. That inspection caught
literal Markdown emphasis and horizontal-rule markers in PDF output. PDF and
DOCX exporters now format emphasis and omit horizontal rules; PDF inline math
uses a safe readable-text fallback rather than raw TeX commands. DOCX structure
was checked after export; Word/LibreOffice visual rendering is still pending.
The OMR sheet's metadata row was separately fixed after browser checks exposed
mobile overflow; at 390 and 360 widths and print emulation it now fits with no
horizontal document scroll. Its final mobile screenshot is in
`output/playwright/exam-omr-mobile-360-final.png`.

## Audit-to-implementation verification ledger (14 October 2026)

This ledger is checked against the detailed findings in both original reports,
not inferred from the earlier implementation summaries. “Partial” means code
exists but at least one required regression, browser, or deployed check remains.

| Finding(s) | Current evidence/status | Still required |
|---|---|---|
| P1-F01, P1-F02, P2-F08 | DOCX dependency is pinned; authenticated exam download proxy and same-origin link are present; lesson-note PDF/DOCX downloads returned 200, the PDF was visually rendered, and the DOCX structure verified. Worksheet PDF browser download returned 200 with correct saved marks, metadata and no student-facing key. **Partial** | Clean deployment install; exam Word/PDF and CSV/GIFT/QTI browser downloads/error paths; Word rendering; deployed verification. |
| P1-F03 | Title/focus fields exist through the wizard, request/schema, model and migration; revision 0024_exam_metadata_integrity is live. **Partial** | Distinctive title/focus full generate -> job -> detail/list -> export round trip using a QA-labelled record, then remove/retain by explicit ID decision. |
| P1-F04, P1-F05 | Workflow filters/counts and shared state rendering are implemented in API/dashboard/list code. **Partial** | Add or run contract tests proving every status partitions exactly once and dashboard/list/detail agree against representative API responses. |
| P1-F06, P1-F14 | API/source fields and UI fallbacks now distinguish AI/manual and use creator name or “Unknown,” not a fabricated staff name. **Partial** | Verify actual AI/manual rows and creator attribution in browser and exported documents. |
| P1-F07 | UI distinguishes absent quality data from a numeric score in the current implementation. **Partial** | Test no-report, zero, and scored reports; confirm neutral styling and dimension/overall consistency. |
| P1-F08 | Removed inline `hx-on` handlers from the wizard and Question Bank delete modal; both use registered HTMX listeners. Empty and valid wizard submissions were browser-tested after the change with zero console errors. **Locally verified** | Repeat CSP check on deployed build and audit any future dynamically emitted markup. |
| P1-F09, P2-F10 | Base table rule owns horizontal scrolling; app content/main are shrinkable; phone topbar constraints apply through 399px. Exam list and detail were browser-measured at 1440/1024/390/360 with no page overflow; mobile title ellipsis leaves the kebab menu visible, while the 1024 table scrolls locally and is keyboard-operable. **Implemented; local browser-verified** | Repeat checks against deployed build. |
| P1-F10, P2-F09 | Settings and exam/print image markup carry one-time local brand fallback; print waits briefly for fallback; PDF logo fetch is bounded to 4 seconds and falls back to bundled mark. Student print browser view loaded the fallback without a broken-image glyph. **Fallback locally verified; remote storage unresolved** | Investigate intermittent Storage/CDN 504; test valid/404/slow object paths and generated PDF placement in deployed environment. |
| P1-F11, P1-F17 | Week warning is hidden until validation and wizard step labels use a stable Curriculum label. At 390px an empty submit stays on Step 2, shows the warning and resets Next; selecting a valid week advances to Step 3. **Browser-verified** | Check post-generation stepper on a successful deployed run. |
| P1-F12, P2-F13 | Titles are emitted in `<head>` with branded defaults; explicit titles are present for audited routes. Browser title sweep covered Start, Curriculum, Administration, Teaching, Exams, Feedback, exam detail and student print. **Locally verified** | Deployed title smoke check; maintain route coverage for new pages. |
| P1-F13 | `/login` now redirects an authenticated session to `/app`; logout's one-shot flash is displayed once and consumed. **Implemented; regression-tested** | Confirm the expired-session login flow in browser and the internal-operator logout message too. |
| P1-F15 | Manual question removal now opens a Faststrap confirmation. At mobile width, Keep question left both questions intact; confirming Remove question removed only the selected card, closed the modal, and preserved the remaining card. **Implemented; mobile browser-tested** | Verify keyboard-only activation/focus return and confirm the last-question safeguard. |
| P1-F16 | Exam detail cards pluralize marks; print PDF uses compact [Nm] rather than [1 marks]. **Source-verified** | Inspect rendered student/answer/OMR exports and ensure all relevant print formats use correct singular/plural wording. |
| P2-F01, P2-F02 | Read-only exported retained QA worksheet PDF confirms saved marks (37 total), Mathematics/SSS 3/First Term metadata, and one-page layout; answer-key text is absent from learner output. **Representative record verified** | Verify legacy worksheet rows and a new worksheet only in an explicitly approved QA workspace; deployed export check. |
| P2-F03 | **Withdrawn by the audit. Do not implement as a defect.** | No action; preserve only as optional idempotency hardening, not release blocker. |
| P2-F04 | Teaching shell now consumes pop_flash(req). **Source-verified** | Exercise success/error for all Teaching actions and prove each flash appears once and never leaks to another route. |
| P2-F05 | Teaching reads are bounded/concurrent with partial rendering. Exam detail fetch is now bounded, duration/status logged, and transient failures get a safe retry page. **Partial** | Reproduce Teaching and exam detail under deployed concurrent generation; analyze observed timings and source of 504; confirm retry and expired-session handling in browser. |
| P2-F06 | Dirty note refinement shows a Faststrap confirmation; mobile browser check confirms Keep editing preserves text, sends no refinement request, restores the action immediately instead of leaving it spinning, and returns focus to the triggering action. **Partial** | Test Replace, clean/saved note, and expired-session behavior. |
| P2-F07 | Lesson-note PDF and editable DOCX actions, tenant-scoped API endpoints, and signed-session frontend proxies exist; authenticated browser fetch returned 200 for both. The two-page PDF was rendered and visually reviewed; Markdown formatting was corrected. DOCX structure verified. **PDF locally visually verified; DOCX structurally verified** | Render DOCX in Word/LibreOffice; inspect long-note pagination and tables/formulas. |
| P2-F11 | Full week topics appear in an expandable, screen-reader-readable list adjacent to the selector. **Implemented; responsive layout checked** | Check long topics with keyboard and a screen reader. |
| P2-F12 | Structured authoring provides up to 20 question rows with type, marks, options, and staff-only key; schema validates MCQ options. Retained worksheet PDF visually inspected; marks/options present and no answer key leaked. **Representative export verified** | Legacy-row coverage and deployment check. |
| P2-F14 | Coverage cards, metrics and warning explicitly state school-wide scope and staff/admin responsibilities; live workspace showed the one-started/zero-taught state and the same clear denominator across scope refreshes. **Empty/partial state locally verified** | Verify taught/verified success state and confirm copy with pilot school staff. |
| P2-F15 | Note/question controls have visible labels/descriptions; refinement, add/remove-question, and dirty-modal actions measure 44px at both 390px and 360px; outline variants retain brand contrast; Teaching renders without document overflow at 360px. Browser tested cancel/refocus and preservation of dirty text. **Touch/layout locally verified** | Keyboard and assistive-technology review. |
| P2-F16 | `_scope` re-fetches subjects for the requested class: Primary-to-SSS and SSS-to-Primary resets an unavailable subject with explanatory notice; Mathematics remains selected as a valid shared subject. **Browser-verified** | Deployed smoke check. |

Audit-identified blocked scenarios remain separately tracked in Phase 6. Still
open are provider-failure/retry and slow-network paths, empty curriculum,
exam-export pagination and long-title output, approval-chain coverage, OMR
scoring correctness, Mermaid support (not currently claimed in Teaching),
refresh during generation, deployed concurrency/storage checks, and Word
visual rendering. OMR layout is responsive-verified; its scoring behavior is
not.

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
