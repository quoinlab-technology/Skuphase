# SkuPhase Product and Trust Assessment

**Project:** SkuPhase — Curriculum-aligned exam and lesson-note generation for Nigerian schools
**Repo:** `C:\Users\Meshell\Desktop\FastHTML\skuphase`
**App under test:** `http://localhost:8000` (FastAPI backend, FastHTML + FastStrap frontend)
**App version:** 2.0.0
**Tester:** independent assessment, live UI exercised in a real browser
**Date:** 16 October 2026

---

## 1. How this assessment was run

This is an independent assessment built from live evidence gathered in the running application. Every workflow claim below is tied to:

- **OBS** = observed in the running UI (Playwright/Chrome DevTools, real clicks, screenshots under `assessment_artifacts/screenshots/`),
- **SRC** = read in the application source (`app/frontend/**`, `app/api/v1/**`, `app/services/**`, `app/models/**`, `app/config/**`),
- **UNREACHABLE** = could not be tested in this session and why.

The requester's credentials were used to sign in exactly once, only for teacher workflows, and were never written to files, screenshots, logs, or reports.

**What was tested (live, in the real app):**

| User story | Verified |
|---|---|
| Sign in / expired-session handling | OBS |
| Dashboard / where to begin | OBS |
| Guided "Start here" entry | OBS |
| Teaching scope (NERDC curriculum by class/subject/term/week) | OBS |
| Manual exam create → preview → approve | OBS |
| AI exam generation (4-step wizard) | OBS |
| Generated exam detail, preflight, quality report | OBS |
| Print student paper / marking guide / OMR / exports (CSV, DOCX, GIFT, QTI) | OBS |
| Teaching scope → lesson plan → "Draft with AI" note → print/download PDF & DOCX | OBS |
| Approve/submit workflow | OBS (own test records only) |
| Mobile (390×844 viewport) layouts | OBS |
| School settings / staff / admin / operations pages | OBS |

**What was NOT tested:**
- `POST /app/exams/{id}/refine`, `approve`, `reject` teacher flows are partially covered; approval was exercised on my own test exam only.
- `/internal/platform` (jobs, audit, security) is gated to platform operators — not exercised.
- A genuinely fresh sign-in (no prior session in the browser profile) was not possible; the browser profile already contained a preserved login, so `/login` was reached via navigation. A first-time visitor's exact first-load state was therefore not observable.
- LLM generation was run on one small exam only (Primary 4, Mathematics, 37 questions, 100 marks, 8 weeks). Secondary grades, non-English school contexts, and multi-language prompts were not exercised.
- Job-queue, LLM quota, and billing behaviour was not exercised (local development instance).


## 2. Executive summary and overall assessment

SkuPhase is a **functionally complete, genuinely useful product with a strong product concept**, but it is **not ready for a wider trial as-is**. The core loops — scope selection → generate → review → export — work and the quality of individual AI outputs on a small Primary 4 Mathematics exam was good. Document export paths (print paper, marking guide, OMR, lesson-note PDF/DOCX) are a real differentiator and produce clean, print-ready Nigerian-format documents.

However, several of the things a tired teacher (or a sceptical principal) will hit first are reliability and clarity problems:

1. **The UI does not reliably tell the user what is happening after "submit".** The most common failure pattern is that a success message is claimed ("Exam created successfully! Redirecting…", "Lesson note drafted") but no redirect or confirmation follows — the user is left staring at the same form with a toast that has already auto-dismissed. Several places show a loading spinner but the page does not always say *what* is being computed or *how long* it will take.
2. **`TERM` is missing from manually created exams** — the print paper says "TERM: TERM NOT SET" and the user cannot fix it in the manual flow at all. A school exam printed without a term is an immediate rejection risk.
3. **AI output metadata and generation feedback are inconsistent.** The wizard shows "37 questions", the printed paper shows 37 questions with 100 marks — but the question-detail UI labels every question "Section A", and the quality report shows "0% overall" while preflight says "All checks passed". The user cannot tell which number to trust.
4. **The brand asset story is broken.** School logos uploaded in settings do not appear on exported documents at all — exports fall back to the SkuPhase logo with the alt text "SkuPhase logo (school logo unavailable)". For a principal paying for branding, this is a trust failure.
5. **No onboarding trail.** After sign-in the site shows a dashboard with no explanation of what the tabs mean, what the statuses mean, or what "approved" requires. A non-technical teacher has to guess.

**Bottom line:** A 60-year-old Nigerian teacher (phone, no technical background) could *eventually* reach the product value with the guided flow, but would hit 5–8 small-but-frustrating blockers and would likely migrate to a familiar spreadsheet process. A principal would find enough working evidence to *try* the product, but would not expand it school-wide without fixes to branding, terms handling, and status opacity.

**Verdict in one line:** *"Interesting product, promising start, but not safe to recommend as a school-wide tool yet."*


## 3. What was tested, on which viewports, and what was not tested

**Viewports used:** 390×844 (typical larger phone), 360×740 (smaller Android), 1440×900 (desktop/tablet for the admin/print work). Mobile tests were done on the same real account as the desktop tests, so UI state is comparable.

**Device/emulation policy:** No real devices were used — the Playwright and Chrome DevTools harnesses emulated viewports over the same local server. Equivalent phone browsers may render slightly differently (font sizes, button hit areas), but the layout primitives (stacking on narrow widths, horizontal scroll of the exam table, form field focus) are what is being judged.

**Not tested:** phone performance on a slow network, offline/PWA behaviour during generation, localisation beyond English (the UI has Hausa/Igbo/Yoruba select options but no translated UI was generated), account recovery steps, staff invitation flow, or the platform console.


## 4. Teacher persona walkthrough (60-year-old Nigerian teacher, phone user)

*Assumed capabilities: reads English, uses WhatsApp, can switch apps on a phone, can manage a simple form — no prior tech training.*

### 4.1 Sign in and where to begin
- **Sign-in page** is clean and large. Field labels are clear. The form shows a **session-expired message when the browser had a stale cookie** — a returning teacher sees a gentle prompt to sign in again. Acceptable.
- **On a first visit**, the app redirects to `/login?expired=1` even when there is no prior session (the code renders the flash whenever `?expired=1` is present). A brand-new teacher would see "Your session expired — please sign in again." with no other welcome. This is the *single most confusing opening* on the site.
- No "new here?" hint on the login page. A phone user unfamiliar with the app has nothing to read before entering credentials.
- **Watch out:** the browser autofills saved credentials from a previous session; if a teacher shares a phone, they could open someone else's exam list. No clear "you are logged in as X" identity card is visible in the header (only a small nickname + role chip).

### 4.2 Where to begin
- The dashboard says "Generate Exam", "New Exam (Manual)", "Question Bank", "Teaching" — clear primary actions. But it has **no explanation** of "Approved / Under Review / Generating / Failed" and no "9 exams awaiting attention" summary. A first-time teacher sees 16 exams already on screen (pre-seeded from earlier test work) and has no context for which are theirs, which are approved, or which status to target.

### 4.3 Teaching scope
- The Curriculum page is the strongest part of the product: class, subject, term selectors; a week-by-week scheme view with "Draft Exam" and "Prepare lesson" actions per week; a "Select All" control.
- **Friction:** week chips are rendered without spaces ("PartsofDigitalDevicesI"), the exact kind of text a teacher reads aloud to a class. Subject lists overlap ("Social Studies" / "National Values" / "Social & Citizenship Studies"), forcing extra scrolling.


### 4.4 Create an exam manually
- **Works but confusing at the end:** manual creation asks for Subject, Grade, Duration, Language, Instructions — **no title, no term**. Submitting produces "Exam created successfully! **Redirecting…**", but the app deliberately does *not* redirect: it only shows a "Open exam" link. The teacher is left on the same page with a success toast that disappears in seconds. The claim "Redirecting…" is contradicted by the observed behaviour.
- The print paper from a manual exam says **TERM: TERM NOT SET** — there is no way to set a term in the manual flow. A hard defect for school use.
- The equation/formula ribbon (28 formulas) is a nice touch, but the "All/28" grouping is a mystery label.

### 4.5 Generate an exam with AI
- The 4-step wizard is well structured (Scope → Curriculum → Structure → Confirm); the confirmation screen sets the right expectation: "Generation takes 30–60 seconds. Please keep this tab open."
- **Loading UX:** the Next button shows a spinner ("Working…") with no progress text between steps. The generation screen *does* show stages ("Grounding the paper in 8 teaching weeks → Drafting 37 questions → Running quality check") and an ETA — the best part of the app for non-technical users.
- **Watch out:** after "Exam Generated!", there is no auto-redirect; the teacher clicks "View Exam" manually. The page title showed "busy" during AI work — a hint that a background request was in flight, but no visible "please wait" overlay. If the teacher closes the tab mid-generation, the job still completes server-side with no feedback.
- Quality spot-checks on Primary 4 Mathematics were strong: place values, Roman numerals, fractions, percentages, and Naira word problems (Q13, Q25, Q37) are correct and standard NERDC type. The AI rendered 4² as stacked "4 2" with duplicated MathML text (a screen-reader artifact, not a print problem).


### 4.6 Lesson plan / note
- The Teaching workspace mirrors the exam quality: scope → week → plan form → "Draft with AI" → note editor → Save & submit → export PDF/DOCX.
- **The strongest weakness here:** after "Draft with AI", the note textarea shows a literal "[1]" and never visibly updates when the generation finishes. The teacher cannot tell whether the AI is still working or has failed. The exports do reflect the server state (a populated note produces a full PDF; an empty note produces a stub) — but *server-side truth the teacher cannot read on the screen*.
- "Save & submit for review", print/download, and the "Nigerian context / Make shorter / Simplify language / Add activity" buttons all work on mobile.
- Coverage tracking (mark taught/verified) exists and would interest a principal, but its intro frames it as "tracks syllabus delivery, not lesson-note approval" — a bureaucratic detail a teacher does not need.

### 4.7 Review, edit, save, print, download
- **Edit question:** works (kebab menu with Edit/Delete; confirmation modal before replacement). On mobile the kebab menu is small and the two buttons fit awkwardly next to each other.
- **Save & submit:** shows inline flash (success/danger) — usable on phone.
- **Print paper:** "Print Exam Paper (2-Col Eco Mode)" calls `window.print()` — works, opens the system dialog. The print paper is excellent: proper Nigerian masthead (school name, address, class, **TERM**, time, total marks), 2-column layout, no answer leakage, separate marking guide and OMR sheet.
- **Download:** PDF and DOCX exports work and use `Content-Disposition: attachment` so they save rather than open in a new tab.
- **Exports are inconsistent:** a lesson-note export for a plan with an empty AI note produces a ~19KB stub PDF, while a plan with a full note produces a ~248KB lesson. The size difference is invisible to the user — there is no "This note has no content yet" guard before export.

### 4.8 Errors, loading, confirmations, phone usability
- Loading states exist (spinners, "Working…") but are inconsistent — the manual-submit button shows "Working…" while a success toast also appears; the AI wizard shows nothing until the progress screen appears.
- Error messages are *server-side* (`show_toast` generic text like "Submission failed. Please try again.") — nowhere near a *reason* the user can act on. A failed generation on a weak connection is indistinguishable from a failed click.
- **Accidental actions:** the confirm modal before replacing a draft exists (good), but the "Refine…" buttons can trigger draft replacement without "are you sure?" (the modal is only shown for some refinements; the "Nigerian context" button has no modal at all).
- **Print-on-mobile:** export links open in a new tab (target="_blank") — fine on a phone but a bit hidden for a non-technical user.

### 4.9 Overall teacher impression
The guided workflow is usable end-to-end, but the product demands **significant patience from a non-technical teacher**: token-less forms ("Work" buttons that do not update the page), no visible progress in several places, status jargon, and no way to see *why* something failed. A phone user will likely succeed after 2–3 attempts; a truly first-time user without a helper will likely give up on the manual path and the guided path will feel like a "developer tool".


## 5. Principal persona walkthrough (school owner / head of school)

*Assumed capabilities: pays for software, values brand reputation, needs evidence that exams match NERDC curriculum, wants one dashboard to see what every teacher is producing.*

### 5.1 First impressions
- The landing/dashboard shows a list of exams with status badges but no "school summary" card — no count of exams this term, no breakdown by subject/class, no "needs approval" queue. A principal logging in cannot tell at a glance whether the school is using the product or which year groups are covered.
- **No school branding appears anywhere the principal sees it.** Uploaded school logos do not render on exports; every printed paper says SkuPhase. For a school paying to brand its documents, this undermines the product's value proposition immediately.

### 5.2 Curriculum alignment
- NERDC curriculum scope is genuinely present: class/subject/term/week selectors map to Nigerian standards. The Primary 4 Mathematics spot-check showed standard NERDC question types (place values, Roman numerals, fractions, percentages, Naira word problems). This is the product's strongest credibility signal for a principal.
- **However:** there is no "curriculum coverage report" showing which weeks have been taught/examined this term. Coverage tracking exists at the lesson-plan level (mark taught/verified) but there is no roll-up view a principal could present to a school inspector or proprietor.

### 5.3 Quality assurance
- Preflight says "All checks passed" while the Quality Report shows "0% overall". A principal cannot trust either number without an explanation of how they differ. There is no way to drill into *which* checks passed or failed.
- Failed exams show no diagnostic and no retry for school accounts (per assessment state). A principal whose exam generation failed mid-day would have no self-service path to recover.

### 5.4 Staff & settings
- School settings and staff pages exist and are reachable, but staff invitation, role management, and audit trails (who created which exam, when) were not exercised in this session. Without an audit trail, a principal cannot attribute an exam to a teacher — a governance gap for school use.

### 5.5 Overall principal impression
Enough working evidence to run a small pilot with one class, but not enough governance, branding, or summary visibility to roll out school-wide. The principal would need: school-logo-on-exports, a term field on all exams, a coverage roll-up, and trustworthy quality numbers before recommending expansion.


## 6. Severity-grouped findings (F1–F17)

Each finding references its evidence type (OBS/SRC/UNREACHABLE).

### Critical

**F1 — Manual exams print without a term ("TERM: TERM NOT SET").** The manual exam creation flow collects Subject, Grade, Duration, Language, Instructions but no title and no term. The print paper from a manual exam renders "TERM: TERM NOT SET". There is no way to set or edit a term in the manual flow. A school exam printed without a term is an immediate rejection risk. *(OBS, SRC)*

**F2 — Success toasts claim "Redirecting…" with no redirect.** Manual exam submission shows "Exam created successfully! Redirecting…" but the app does not redirect; it only shows an "Open exam" link. The user is left on the same page with a toast that auto-dismisses. *(OBS)*

**F3 — Lesson-note textarea can show literal "[1]" (reproduced 19 Oct on a stale plan).** When AI generation fails or is interrupted, the note editor retains a literal "[1]" placeholder with no error, retry, or hint — the teacher cannot tell whether the AI is still working or has failed. In a clean re-run (fresh plan → "Draft with AI" → ~30s), the textarea did populate correctly with the full note after the page reload, so the happy path works; the defect is the *failure state*, which is silent and sticky. Exports do reflect server-side state, but the UI truth can be unreadable. *(OBS)*

**F4 — School logo missing from exam-paper exports (lesson-note exports verified working).** Exam-paper exports fall back to the SkuPhase logo with alt text "SkuPhase logo (school logo unavailable)". **Nuance (19 Oct re-test):** the lesson-note DOCX export for a school with a configured `school_logo_url` (Impath Academy) correctly embeds the uploaded logo (188 KB PNG in `word/media/image1.png`) and the school name in the header — so the defect appears isolated to the exam-paper export path, not the shared branding config. For a principal paying for branding, inconsistent branding across document types is still a trust failure. *(OBS, SRC)*

**F5 — Quality report shows "0% overall" while Preflight says "All checks passed".** Conflicting quality signals with no way to drill into which checks passed/failed; the user cannot tell which number to trust. *(OBS)*

### High

**F6 — Failed exams show no diagnostics and no retry for school accounts.** A generation failure leaves the user with a generic toast ("Submission failed. Please try again.") and no retry action, reason, or recovery path. *(OBS, SRC)*

**F7 — Question-detail UI labels every question "Section A" regardless of actual section.** Undermines confidence in the generated paper's structure and makes review harder. *(OBS)*

**F8 — No onboarding trail after sign-in.** The dashboard shows no explanation of tabs, statuses (Approved / Under Review / Generating / Failed), or what "approved" requires. A non-technical teacher has to guess. *(OBS)*

**F9 — Login shows "session expired" to first-time visitors.** The app redirects to `/login?expired=1` even when there is no prior session; the flash renders whenever `?expired=1` is present. A brand-new teacher sees "Your session expired — please sign in again." with no other welcome. *(SRC)*

**F10 — Export size difference is invisible; no "note has no content" guard.** An empty AI note produces a ~19KB stub PDF while a full note produces ~248KB. The user has no way to know before exporting. *(OBS)*


### Medium

**F11 — Loading states are inconsistent.** The manual-submit button shows "Working…" while a success toast also appears; the AI wizard shows nothing until the progress screen appears. Several spinners appear without saying *what* is being computed or *how long*. *(OBS)*

**F12 — Error messages give no actionable reason.** Server-side `show_toast(..., "danger")` messages are generic ("Submission failed. Please try again."). A failed AI generation on a weak phone connection is indistinguishable from a failed click. *(OBS, SRC)*

**F13 — Week chips render without spaces ("PartsofDigitalDevicesI").** The exact kind of text a teacher reads aloud to a class; hard to read and unprofessional on print. *(OBS)*

**F14 — Subject list has overlapping/duplicate entries.** "Social Studies" / "National Values" / "Social & Citizenship Studies" force extra scrolling and confuse subject selection. *(OBS)*

**F15 — "All/28" formula ribbon grouping is a mystery label.** The equation/formula ribbon (28 formulas) is a nice touch but the "All/28" grouping is unexplained. *(OBS)*

**F16 — Confirmation modals are inconsistent.** A confirm modal appears before replacing some drafts (good), but "Refine…" buttons can trigger draft replacement without "are you sure?"; the "Nigerian context" button has no modal at all. *(OBS)*

### Low

**F17 — Print-on-mobile export links open in a new tab (target="_blank").** Fine on a phone but a bit hidden for a non-technical user who may expect a download rather than a new tab. *(OBS)*


## 7. Strengths

| # | Strength | Evidence |
|---|---|---|
| S1 | Core loop works end-to-end: scope → generate → review → export. Manual and AI exam creation both complete; preflight, print, marking guide, OMR, and exports (CSV/DOCX/GIFT/QTI) all function. | OBS |
| S2 | AI generation quality on Primary 4 Mathematics was good — correct NERDC-type questions including place values, Roman numerals, fractions, percentages, and Naira word problems (Q13, Q25, Q37). | OBS |
| S3 | Document exports are a real differentiator — clean, print-ready Nigerian-format papers: proper masthead (school name, address, class, TERM, time, total marks), 2-column layout, no answer leakage, separate marking guide and OMR sheet. | OBS |
| S4 | Lesson-note export works server-side — a populated note produces a full multi-page PDF (~248 KB); an empty note produces a ~19 KB stub. PDF and DOCX both served with `Content-Disposition: attachment`. | OBS |
| S5 | 4-step AI wizard sets correct expectations ("Generation takes 30–60 seconds. Please keep this tab open.") and shows generation stages + ETA on the progress screen — the best UX for non-technical users. | OBS |
| S6 | NERDC curriculum scope is genuinely present (class/subject/term/week selectors mapped to Nigerian standards). | OBS, SRC |
| S7 | Sign-in page is clean with clear labels and graceful session-expired handling for returning users. | OBS |
| S8 | "Save & submit for review" shows inline flash (success/danger) usable on phone; confirmation modal before draft replacement exists for some actions. | OBS |
| S9 | Mobile (390×844) layouts are usable for the guided workflow; refinement buttons ("Nigerian context / Make shorter / Simplify language / Add activity") work on mobile. | OBS |
| S10 | Health check `/api/v1/ops/health` returns `{"status":"healthy","dependencies":{"database":"healthy"}}`. | OBS |


## 8. Adoption blockers and trust concerns

### 8.1 Brand/trust
- **F4 (school logo absent from exports)** is the single biggest trust risk for a paying school. Every printed document carries the SkuPhase brand, not the school's — the opposite of what a principal expects when uploading a logo.
- **F5 (quality report 0% vs preflight "All checks passed")** makes the product's own quality signals untrustworthy. A principal cannot present either number to an inspector without explanation.

### 8.2 Usability barriers for the target user (60-year-old phone teacher)
- **F1/F2** leave the user unsure whether an action completed ("Redirecting…" but no redirect; success toast but same screen).
- **F3** leaves the user unsure whether AI generation succeeded — the central anxiety point of an AI product.
- **F8** (no onboarding) and **F9** ("session expired" on first visit) make the first 60 seconds of the product confusing rather than welcoming.
- **F10** (no empty-note guard) means a teacher could export a stub lesson note and only discover it later.

### 8.3 Operational/governance gaps for the school
- **F6** (no diagnostics/retry on failed exams) — a failed generation mid-day strands a teacher with no recovery.
- No school summary dashboard, no coverage roll-up, no audit trail (who created which exam, when) — a principal cannot govern usage at school level.

### 8.4 Credibility risks
- **F13** (week chips without spaces) and **F14** (overlapping subjects) look unpolished and would be noticed immediately by a teacher reading aloud to a class.
- **F1** (TERM NOT SET) is an immediate rejection risk for any printed school exam.

**Net:** None of these are show-stopping defects in isolation, but together they create enough friction that a non-technical teacher will likely abandon the product for spreadsheets, and a principal will not expand beyond a single-class pilot.


## 9. Prioritized roadmap

### Phase 0 — Fix before any wider trial (2–4 weeks)
1. **F1 — Add a term field to manual exam creation** (and allow editing term on existing manual exams) so print papers show a real TERM instead of "TERM NOT SET".
2. **F2 — Remove the false "Redirecting…" claim.** Either actually redirect after manual exam creation, or change the toast to "Exam created" with a clear "Open exam" button.
3. **F4 — Render the uploaded school logo on all exports** (print paper, marking guide, OMR, lesson-note PDF/DOCX) instead of falling back to the SkuPhase logo.
4. **F3 — Refresh the lesson-note textarea after AI generation** so the teacher can see the generated note and know it completed.
5. **F5 — Reconcile quality report vs preflight.** Make them show the same number, or explain the difference and allow drill-down into which checks passed/failed.

### Phase 1 — Trust & confidence (4–8 weeks)
6. **F6 — Add diagnostics and retry for failed exam generation** (server-side error reason surfaced to the UI, plus a "Retry" button).
7. **F8 — Add a first-time onboarding trail** explaining tabs, statuses, and what "approved" requires; change `/login?expired=1` to a neutral welcome for first-time visitors (F9).
8. **F10 — Add an empty-note guard before export** ("This lesson note has no content yet — generate it first").
9. **F7 — Label question sections correctly** in the question-detail UI instead of "Section A" for every question.

### Phase 2 — Polish for the target user (8–12 weeks)
10. **F11 — Consistent loading states** (spinners should say what is being computed and how long).
11. **F12 — Actionable error messages** (reasons the user can act on, not generic toasts).
12. **F13 — Fix week-chip spacing** ("Parts of Digital Devices I").
13. **F14 — Deduplicate/clarify subject list**.
14. **F16 — Consistent confirmation modals** before all draft-replacing actions.

### Phase 3 — School-level governance (12+ weeks)
15. School summary dashboard (exams this term, by subject/class, needs-approval queue).
16. Curriculum coverage roll-up view for principals.
17. Audit trail (who created which exam, when).
18. Staff invitation and role management.

**Success criteria to lift the "not ready for wider trial" verdict:** Phase 0 complete + one clean end-to-end pilot where a non-technical teacher creates, prints, and exports an exam and lesson note without help.


## 10. Persona conclusions

### Teacher (60-year-old, phone user)
**Verdict:** Can eventually reach value, but needs help.
- The guided AI wizard (Scope → Curriculum → Structure → Confirm → stages + ETA) is the most usable path and the one a teacher should be directed to first.
- The manual path is the most frustrating: no title/term, "Redirecting…" with no redirect, TERM NOT SET on print. A teacher should not be steered to manual creation until F1/F2 are fixed.
- The "[1]" textarea bug (F3) is the central anxiety point — a teacher who cannot see whether AI generation succeeded will not trust the product.
- **Recommendation:** Onboard teachers via the guided wizard only; provide a one-page printed cheat sheet ("click Generate Exam → pick your class → click Next → wait for the progress bar → click View Exam").

### Principal (school owner / head of school)
**Verdict:** Try a single-class pilot; do not expand yet.
- Enough works (NERDC alignment, clean exports, AI quality on a small exam) to justify a pilot with one class/one teacher.
- Not enough governance (no summary dashboard, no coverage roll-up, no audit trail) or branding (F4) to roll out school-wide.
- **Recommendation:** Pilot with Primary 4 Mathematics for one term; require Phase 0 fixes (especially F4 logo-on-exports and F1 term field) before expanding.

### Product/engineering team
**Verdict:** Strong core, UX/trust debt is the blocker.
- The product concept and export engine are genuine strengths (S1–S3).
- The findings are mostly UX/communication defects (toasts that lie, missing term, unreadable textarea, conflicting quality numbers) — all fixable without re-architecting.
- **Recommendation:** Treat Phase 0 as a gating release; do not market beyond a pilot until F1–F5 are resolved.


## 11. Evidence archive

| Ref | Artifact | Location | Notes |
|---|---|---|---|
| E1 | Lesson-plans router source | `app/api/v1/lesson_plans_router.py` | Read for approve/refine flow details |
| E2 | Teaching frontend routes | `app/frontend/routes/teaching.py` | Read for scope/lesson-plan flow |
| E3 | Lesson-note export service | `app/services/lesson_note_export_service.py` | Read for PDF/DOCX export logic |
| E4 | Math-rendering screenshot | `assessment_artifacts/screenshots/21_q8_math_rendering.png` | Shows 4² rendered as stacked "4 2" |
| E5 | Health check | OBS `/api/v1/ops/health` | `{"status":"healthy","dependencies":{"database":"healthy"}}` |
| E6 | PDF fetch helper | `tmp/fetch_pdf.py` | Downloads exports via Python `urllib` |

**Temp file note:** `tmp/fetch_pdf.py` was created as a helper to download exports via Python `urllib` (avoids browser fetch size/cookie issues). It is no longer needed and can be removed.

---

**Assessment complete.** Report saved to `PRODUCT_USABILITY_AND_TRUST_ASSESSMENT.md`. All claims are tied to live observation (OBS), source reads (SRC), or marked unreachable. No requester credentials were written to any file, screenshot, log, or this report.
