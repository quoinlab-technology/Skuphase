# Exam Generation Flow — End-to-End Production Audit

**Date:** 2026-09-04 · **Scope:** the production lane only — click "Generate with AI" → wizard → generation polling → exam detail → correcting a question → preflight / quality / audit comments → export PDF & browser print.
**Method:** function-by-function read of `routes/exams.py` (2,965 lines), `components/exam.py`, `core/workflow.py`, `api/v1/exams_router.py` (export/refine/preflight paths), `services/export_service.py`, `frontend/deps.py` + `middleware.py`, print CSS. Every claim below cites file:line.

---

## Verdict

The **generation half** of the lane is solid: wizard steps, payload assembly, polling screen, state machine, preflight gating and the comments/refine loop are all wired and correct. The **output half is not production ready**: the exported PDF **cannot be downloaded** from the browser (auth dead-end), the printed paper's school header is **always empty or wrong** (missing data in the session), the PDF **never renders the school logo** despite accepting it, MCQ options print **without letter prefixes**, there are **no section headers** on paper, and — most importantly for the "correct a question" step — **questions are immutable by design with no edit UI anywhere**.

## CRITICAL — blockers on the production lane

### C1. The "Download PDF" link always fails with 401 in a real browser
- `exams.py:2944–2949` — after a successful export the UI returns a plain `<a href="/api/v1/exams/{exam_id}/exports/{file}">` link (same pattern at `exams.py:858` in the Exports-history modal).
- That URL is served by `exams_router.download_export` → `Depends(get_current_user)` (`core/dependencies.py`) which reads **only** `HTTPBearer` Authorization headers. A browser navigating a plain link sends the session cookie but **no** `Authorization` header → 401/403 every time.
- Tests pass because they inject the header manually (`tests/test_exams_router.py:194,647,669,679`). No test clicks the link the way a user does.
- **Impact:** the entire export lane terminates in a dead end for every user. Browser print is the only workaround, and it inherits C2.

### C2. The printed school header is always empty or falls back to nonsense
- `exams.py:998–1003` builds the print-only header from `user.get("school_name")`, `user.get("school_address")`, `user.get("school_logo_url")`.
- The session user dict is stored verbatim from `TokenResponse.user` (`deps.py:store_auth`) which is a `UserResponse` — and `UserResponse` (`schemas/auth.py`) contains **only** `user_id, full_name, email, role, account_type, is_active, is_verified, created_at`. **No school fields exist.**
- Result on every print: logo never renders (`school_logo` always `""`), address never renders, and school name falls back to `or "FEDERAL REPUBLIC OF NIGERIA"` (`exams.py:998`) — a wrong, embarrassing header on a real exam paper. Same root cause makes the sidebar show the hardcoded "Greenfield Academy" for school users whose data is absent (`layout.py:277`).
- **Impact:** the user's stated requirement — "clean standard school question paper with school name, logo at the side and address" — is not met at all in the browser-print lane.

### C3. Questions cannot be corrected — by design, with no alternative except a 20–60 s AI gamble
- `components/exam.py:QuestionBlock` is strictly read-only; grep across `frontend/**` finds **no** per-question edit UI.
- Backend is explicit: `exams_router.update_exam` — *"Cannot update questions (exams are immutable once generated)"*. `ExamUpdateRequest` only allows status/instructions/duration.
- The only correction paths today: (a) whole-exam AI refine with free-text feedback (`/ui/exams/{exam_id}/refine`, min 5 chars) and hope the LLM fixes the exact question, 20–60 s round trip; (b) regenerate the exam; (c) save the question to the bank and edit it *there* (`bank.py:461`) — but the exam copy stays wrong.
- **Impact:** a teacher who spots one wrong option on a 40-question paper has no reliable fix. For an exam-generation product this is the single biggest functional gap.

## HIGH

### H1. The PDF export never renders the school logo
`export_service.export_exam_pdf` accepts `school_logo_path` (`export_service.py:66`) and the API dutifully fetches it from `SchoolSettings.logo_url` (`exams_router.py` export handler), but the parameter is **never used** — `ReportLabImage` is imported (`~line 79`) and never called; the header (`147–160`) is text-only. The PDF lane therefore also fails the logo requirement even though the data is available.

### H2. PDF prints MCQ options without A./B./C. letter prefixes
`export_service.py:220–222` prints `esc(str(option))` raw. The UI adds `A. `, `B. ` prefixes (`components/exam.py:196–203`), so LLM output stored without letters produces an unanswerable-looking PDF: four bare lines under the question. Frontend and paper disagree.

### H3. PDF prints no section headers — paper is one undifferentiated question stream
The wizard collects `section_title` per section ("Section A: Objectives" etc., `exams_router.py:2110–2114`) and the data model carries it, but `export_exam_pdf` explicitly skips it: `pass  # sections are flattened onto questions by numbering only` (`export_service.py:~200–204`) and `current_section = None  # noqa` is a dead store at the loop tail (`~262`). A Nigerian question paper **requires** `SECTION A — OBJECTIVES (30 MARKS)` headers between groups. Also note H2's sibling: the dead `if q.question_text and getattr(q, "section_title", None): pass` block shows the field was anticipated and abandoned.

### H4. The browser-print lane prints the admin UI, not a question paper
`custom.css:809–830` has a `@media print` block (hides chrome, defines `.print-avoid-break`) but only **one** element in the whole flow carries `no-print` (the refine button, `components/exam.py:169`). Status badges, tab nav, filter pills, Bloom's pills, action buttons and the toast container all flow into a browser printout. There is no dedicated print route — the print lane relies entirely on the PDF export, which is currently dead-ended by C1.

## MODERATE

### M1. Generation polling has no failure ceiling
The poll fragment refreshes indefinitely while the exam is `generating`. If generation wedges (worker crash, stuck row), the user watches "Still generating…" forever with no escape hatch. Add a max-poll count (~60 polls ≈ 3 min) then render "This is taking longer than expected — refresh, or delete this exam and try again."

### M2. Wizard Step 3 never checks the marks total
Sections can sum to ≠ `total_marks` from Step 1 with no client-side warning; the mismatch only surfaces at preflight — after a wasted 2-minute generation. A live "Total: 62 / 100 marks" counter beside the sections list (with a warning style when ≠) prevents this.

### M3. Exports history shows bare UUID filenames
`export_service.list_exports` returns `f"{uuid}.pdf"` names and `exams.py:858` renders them verbatim — meaningless to users. Derive a friendly label from exam metadata + file timestamp at render time (e.g. "Mathematics Paper — 04 Sep, 14:32").

### M4. Export-blocked-by-preflight detail is discarded
When export is blocked, the API returns the structured preflight result inside the 400 detail (`exams_router.py:2038–2042`), but the frontend toast surfaces only `message`; the user must navigate to the Preflight tab to learn *why*. Pass the failing checks into the toast body or auto-open the Preflight tab.

### M5. Answer-key export is indistinguishable from the question paper
`include_answers=True` appends answers inline but prints no "MARKING SCHEME / ANSWER KEY" masthead line — two identical-looking PDFs in a folder is a real risk for a school printing both.

### M6. Refine gives no in-progress state
Whole-exam and per-question refine are async server-side; the UI swaps only on next tab load with no "regenerating…" marker, so a fast user re-opens the tab and sees stale text with no indication anything is happening.

## LOW

| # | Finding | Evidence |
|---|---|---|
| L1 | ~20 inline `style="..."` attributes in the wizard structure step — violates the project's no-inline-style convention, inconsistent with `custom.css` tokens | `exams_router.py:2127–2180` |
| L2 | Default section title `f"Section {chr(64+idx)}: Topics"` renders "A: Topics" — missing the word "Section", inconsistent with the hardcoded defaults above it | `exams_router.py:2124` |
| L3 | Difficulty leaks into the on-screen marks line (`[2 marks] - easy`) — fine for authors, but there is no clean student-view anywhere; harmless while print goes through the PDF lane only | `components/exam.py:226–229` |
| L4 | Audit comments show no open/addressed state, yet refine-from-comments targets "all open comments" — the user can't see what a batch refine will pick up | comments tab renderer |
| L5 | FAILED exam lands on the detail page with a badge and raw failure text but no grouped "Delete and try again" CTA | detail action bar |
| L6 | Sidebar school name falls back to hardcoded `"Greenfield Academy"` — demo data leaking as a prod default | `layout.py:277` |

## User Journey Verdict (walked as a teacher)

1. **Click "Generate with AI" → wizard** — works; 3 steps, prefilled from curriculum deep links. Rough edges: no marks-total guard (M2), inline-style sprawl (L1).
2. **Generate → polling** — works; auto-refresh via poll fragment. No ceiling if generation wedges (M1).
3. **Exam detail → correct a question** — **BROKEN.** No per-question edit exists (C3); the only paths are a whole-exam AI refine gamble or the question-bank round trip that doesn't fix the exam copy.
4. **Validate (Preflight / Comments / Quality)** — works; preflight empty-state + run + gate on export are solid. Failure *reasons* from export-blocking are discarded (M4).
5. **Export → print** — **BROKEN twice.** The PDF download link 401s in a browser (C1). The browser-print fallback prints admin chrome (H4). And even server-side, the PDF is missing the logo (H1), section headers (H3), option letters (H2), and the school header data is absent in the print lane (C2).

**Production-ready lane status: Stages 1–2 ✅ · Stage 3 ❌ · Stage 4 ✅ · Stage 5 ❌**

---

# Implementation Plan (for approval)

## Phase A — Make the printed paper correct (C1, C2, H1, H2, H3, H4) · ~2 days · **highest priority**

**A1. Fix the download dead-end (C1).** Add a session-authenticated frontend proxy route `GET /app/exams/{exam_id}/exports/{file_name}` in `routes/exams.py` that calls the API with the stored token (streaming), tenant-checks, and streams the file back. Repoint the two link builders (`exams.py:858`, `exams.py:2944–2949`). *Alternative considered:* teach `get_current_user` to fall back to the session cookie — more invasive, touches every endpoint; rejected. **Tests:** route streams the file for the owning school; 404/403 for others; links point at the new path.

**A2. School branding resolver (C2).** Extend the login/refresh response (or add `GET /schools/current`) to return `school_name`, `school_address`, `school_logo_url` for school users; store them in the session user dict in `deps.store_auth`; make `layout.py:277` and the print header (`exams.py:998–1003`) consume them, removing the `"FEDERAL REPUBLIC OF NIGERIA"` fallback. **Tests:** header renders real school data; individual teachers get "Personal Workspace".

**A3. PDF masthead with side logo (C2+H1).** In `export_exam_pdf`, build the header as a two-column ReportLab `Table`: left cell = `ReportLabImage(school_logo_path, width≈22mm, preserveAspectRatio=True)` when the file resolves locally (tolerate absence — never fail an export over a logo); right cell = school name + address centered. Wire the already-fetched `school_logo_url` through. **Tests:** export with/without logo yields valid PDFs.

**A4. Section headers on paper (H3).** Group questions by `section_title` in the render loop; emit `SECTION A — OBJECTIVES (nn MARKS)` headers (marks summed from the questions); delete the dead `pass`/`current_section` code. **Tests:** story contains section paragraphs in order.

**A5. Option lettering on paper (H2).** Extract the lettering guard from `components/exam.py:196–203` into a shared util and apply in the PDF path. **Tests:** options with and without stored prefixes render `A. … B. …`.

**A6. Dedicated clean print route (H4).** `GET /app/exams/{exam_id}/print` renders *only* the paper: masthead (A2 data), instructions, sections, questions — no sidebar/topbar/tabs/badges/Bloom pills/difficulty (drops L3 from the paper view), with a `window.print()` CTA and `print-avoid-break` per question. **Tests:** route renders paper + header, none of the chrome markers.

**A7. Answer-key masthead (M5).** When `include_answers`, add "MARKING SCHEME / ANSWER KEY" under the title and a "FOR TEACHER USE ONLY" footer.

## Phase B — Per-question correction (C3) · ~1.5–2 days

**B1. Backend.** New endpoint `PATCH /exams/{exam_id}/questions/{question_id}` in `exams_router.py`: workspace-admin only; allowed only while exam state ∈ {draft, teacher_review} per `workflow.py`; accepts `question_text`, `options`, `correct_answer`, `marks`, `explanation`; writes an audit-log entry ("manual_edit") via the existing `_log_usage` pattern; marks preflight stale so it must be re-run before export. Full-exam immutability stays — this is a surgical exception.

**B2. Frontend.** In `QuestionBlock`, an "Edit" pill (workspace admins, editable states, `no-print`) opens a modal: question text, options (dynamic add/remove for MCQ), correct answer, marks. Submits `hx-post /ui/exams/{exam_id}/questions/{qid}/edit` → calls B1 → returns the updated `QuestionBlock` fragment + `show_toast("Question updated")`; preflight-stale banner appears.

**B3. Tests.** Endpoint permissions (403 teacher/auditor, 403 wrong state), payload validation, audit log written; frontend modal render, fragment swap, toast.

## Phase C — Flow robustness (M1, M2, M3, M4, M6, L5) · ~1 day

- **C1 (M1):** poll fragment counts refreshes (query-param counter); at n ≥ 60 render a timeout empty-state with Refresh + Delete CTAs.
- **C2 (M2):** live "Total: nn / 100 marks" line on wizard Step 3 (server-computed in the sections partial); block submit on mismatch with an inline alert.
- **C3 (M3):** friendly export labels (subject/grade + file mtime) in exports-history and the export-success fragment.
- **C4 (M4):** export-blocked toast includes the top failing checks from the 400 payload + a link opening `?tab=preflight&run=1`.
- **C5 (M6):** refine buttons swap to a disabled "Regenerating…" spinner state; on API return, reload the questions tab.
- **C6 (L5):** FAILED exams render an alert with the failure text + primary "Delete and start over" CTA.

## Phase D — Polish (L1, L2, L4, L6) · ~0.5 day

- Extract wizard inline styles into `custom.css` classes (`.sec-card`, `.sec-input`, …).
- Fix default section title to `"Section A: Topics"` form (consistent with hardcoded defaults).
- Comments list: per-comment `Open` / `Addressed` badge; show the count batch refine will pick up.
- `layout.py:277` fallback → `"Personal Workspace"` for individuals; email-domain placeholder for schools missing a name.

## Order, effort, and approval

| Phase | Effort | Unblocks |
|---|---|---|
| A — print lane | ~2 days | the entire export/print requirement |
| B — question edit | ~1.5–2 days | the biggest functional gap |
| C — robustness | ~1 day | wasted generations, dead-end states |
| D — polish | ~0.5 day | consistency |

**Total ≈ 5–5.5 working days.** Phases A and B are independent and can run in parallel. The existing suite (151 tests) must stay green; every phase ships with the regression tests listed above.

**Recommendation:** approve A + B first. A1 (download proxy) and A3 (PDF masthead) alone convert the export lane from broken to production-ready fastest, and B1/B2 close the "correct a question" gap that no workaround currently covers. Phases C and D can follow in the same or a later sprint.