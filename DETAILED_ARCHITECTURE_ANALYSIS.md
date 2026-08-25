# SkuPhase Deep Architecture and Codebase Audit

Date: 2026-02-28
Scope: Full on-disk review of `SkuPhase/` Python backend, root docs/scripts, and tests.

## 1. Executive Summary

SkuPhase is a FastAPI multi-tenant backend focused on one core problem: generating school exams from uploaded curriculum content using RAG + LLM.

Current state is an advanced prototype, not production-ready. The project has substantial implementation across auth, users, schools, document upload/processing, RAG search, and async exam generation, but there are critical consistency bugs, incomplete modules, documentation drift, and missing test coverage.

Working maturity estimate:
- Auth + tenancy foundations: partially working
- Document ingestion + chunking: partially working
- RAG retrieval quality: low (fallback string match in core path)
- Exam generation end-to-end: partially working, with regeneration bug and weak document scoping
- Operational readiness: low

## 2. Architecture Deep Dive

### 2.1 Layers and Responsibilities

- `app/main.py`: app bootstrap, middleware, router registration, startup/shutdown DB lifecycle.
- `app/config/settings.py`: environment-driven config.
- `app/core/`: infrastructure (DB, auth deps, JWT helpers, LLM client abstraction).
- `app/models/`: SQLAlchemy entities for tenancy, subscriptions, documents/chunks, exams/questions/context, usage logs.
- `app/schemas/`: Pydantic request/response contracts.
- `app/services/`: business logic (auth, user/school, document processing, embeddings, RAG, exam generation).
- `app/api/v1/`: HTTP endpoints mapped to services.

### 2.2 Intended Flow

1. School admin registers and logs in.
2. Admin uploads curriculum documents.
3. Background processing extracts text, chunks, embeds, stores vectors.
4. Exam generation retrieves relevant chunks and calls one LLM request with structured prompt.
5. Generated exam/questions are stored and exposed via CRUD endpoints.

### 2.3 Actual Flow Quality

This flow exists but has high-risk defects:
- Auth routes are mounted with duplicated `/auth` segment.
- Refresh token endpoint expects `access` token, not refresh token.
- User self-checks reference non-existent attribute (`current_user.id`).
- RAG context retrieval ignores provided `document_ids` filter.
- Exam re-generation path does not delete old questions (broken query usage).
- Status values for documents are inconsistent (`processing` vs `in_progress`).

## 3. What Is Implemented (Done)

- FastAPI app lifecycle + middleware + routing registration.
- SQLAlchemy async DB stack and model set for main business entities.
- JWT-based auth + school registration + login + me/logout endpoints.
- School management and user management endpoints/services.
- Document upload to local disk, metadata persistence, async processing endpoint.
- PDF extraction + text cleaning + token-based chunking + embedding attempt.
- RAG service abstraction (vector and text fallback modes).
- Async exam generation endpoint with background task and stored exam/questions/context.

## 4. Current Stage

Practical stage: between "late Phase 2" and "early Phase 3" implementation-wise, but with quality debt equivalent to "Phase 1 hardening pending".

Reason:
- Many features are present in code.
- Core flows have correctness bugs that should be fixed before adding new major capabilities.
- Documentation claims exceed verified implementation.

## 5. What Is Not Done / Missing

### 5.1 Not Implemented at All

- Real migration workflow (no Alembic setup in repo despite dependency).
- Non-empty tests for auth/refinement/exam generation integration.
- Export service (`app/services/export_service.py` is empty).
- Quota/rate-limit service (`app/services/usage_limiter.py` is empty).
- Prompt modules (`app/prompts/*.py`) are empty.
- Permissions/limits modules in `app/core` are empty.
- Question/subscription/settings model modules are empty placeholders.

### 5.2 Partially Implemented

- RAG semantic search (endpoint exists; core search path in `DocumentService` still does literal substring matching).
- Document processing supports PDF path only; DOCX/image/OCR stated in docs is not implemented.
- Regeneration/refinement schemas exist, but no exam refinement endpoint/service flow.
- Billing/analytics tracked in models but not operationalized in services/routes.

## 6. What Is Not Done Well (Key Defects)

1. Route prefix duplication in auth
- `app/main.py:69` mounts `/api/v1/auth`
- `app/api/v1/auth_router.py:24` defines `/auth/register` (and same pattern for login/me/logout)
- Effective path becomes `/api/v1/auth/auth/register`, conflicting with docs.

2. Refresh token logic is incorrect
- `app/api/v1/auth_router.py:72-75` uses `get_current_user`, which enforces `token_type == access` in `app/core/dependencies.py:43`.
- This prevents real refresh-token semantics.

3. User self-protection checks are broken
- `app/api/v1/users_router.py:101` and `:141` compare `current_user.id`, but schema is `CurrentUser.user_id`.

4. Security configuration split and weak fallback
- `app/core/security.py:9` falls back to default hardcoded secret if env missing.
- Expiry in security helper (`ACCESS_TOKEN_EXPIRE_DAYS = 7`) conflicts with API response expectation of 1 hour (`auth_service.py:217`).

5. DB initialization likely incomplete in app startup
- `app/core/database.py:47` calls `Base.metadata.create_all`, but base metadata may not include all models unless imported before startup.

6. School schema typing mismatch
- `app/schemas/school.py:21` expects UUID.
- `app/services/school_service.py:54` and `:163` cast UUID to `str` manually.

7. Document status vocabulary drift
- Model comment says `pending, processing, completed, failed` (`app/models/document.py:29`).
- Runtime uses `in_progress` (`documents_router.py:320,344` and `document_service.py:469`).

8. RAG ignores user-selected documents
- `app/services/exam_generator.py:100-149` accepts `document_ids` but does not filter retrieval by these ids.

9. Exam regeneration cleanup bug
- `app/services/exam_generator.py:466-469` executes `select(Question)...` instead of delete; old questions remain.

10. Document list counting is inefficient
- `app/services/document_service.py:116-118` counts by fetching all rows into memory.

11. Sensitive logging
- `app/services/auth_service.py:46` logs password content.

12. Encoding and text corruption across docs/comments
- Multiple files contain mojibake in comments/log strings, reducing maintainability.

## 7. Documentation Drift

Docs overstate implementation and include mismatched endpoints/features.
Examples:
- `QUICK_REFERENCE.md` lists endpoints not implemented (refine/approve/export analytics/billing paths).
- `PROJECT_ANALYSIS_SUMMARY.md` describes `app/main.py` as empty, but it is implemented.
- Open tabs referenced by user (`PHASE_2_1_PROCESSING.md`, `SUPABASE_CONNECTION_FIX.md`, `install_pgvector.sql`) are not present in current disk snapshot.

## 8. Script-by-Script Status Map

### 8.1 Core Runtime Scripts

- `app/main.py`: implemented; path-prefix issue for auth routes.
- `app/config/settings.py`: implemented; good structure, but LLM env naming is semantically confusing (`grok_base_url` default points to Groq URL string).
- `app/core/database.py`: implemented; uses NullPool and create_all strategy.
- `app/core/dependencies.py`: implemented; strict access-token check, no refresh-token dependency.
- `app/core/security.py`: implemented; config duplication and insecure fallback.
- `app/core/llm.py`: implemented; fallback logic exists, in-memory rate tracking only.

### 8.2 API Routers

- `app/api/v1/auth_router.py`: implemented; incorrect subpaths (`/auth/...`) and refresh behavior.
- `app/api/v1/users_router.py`: implemented; self-check attribute bug.
- `app/api/v1/schools_router.py`: implemented.
- `app/api/v1/documents_router.py`: implemented for upload/list/get/delete/process background.
- `app/api/v1/rag_router.py`: implemented; delegates search.
- `app/api/v1/exams_router.py`: implemented async generation and CRUD; regeneration schema imported but not used.

### 8.3 Services

- `auth_service.py`: implemented; functional but logs password and has token-expiry mismatch assumptions.
- `user_service.py`: implemented.
- `school_service.py`: implemented; UUID string casting mismatch.
- `document_service.py`: implemented; status vocabulary mismatch and non-semantic search in main method.
- `document_processor.py`: implemented for PDF only.
- `embedding_service.py`: implemented; local model first.
- `rag_service.py`: implemented abstraction; separate from `DocumentService.search_chunks` behavior.
- `exam_generator.py`: implemented; major regeneration and retrieval-scoping defects.
- `export_service.py`: empty.
- `usage_limiter.py`: empty.
- `question_manager.py`: empty.

### 8.4 Models

Implemented:
- `base.py`, `school.py`, `user.py`, `plan.py`, `document.py`, `exam.py`, `usage_log.py`

Empty placeholders:
- `settings.py`, `question.py`, `subscription.py`

### 8.5 Schemas

Implemented:
- `auth.py`, `user.py`, `school.py`, `document.py`, `exam.py`, `__init__.py`

Stub:
- `exam_regeneration.py` (empty/minimal)
- `question.py` (empty)

### 8.6 Tests

- `tests/test_exam_generator_v2.py`: only substantial test file.
- `tests/test_auth.py`, `tests/test_exam_generation.py`, `tests/test_refinement.py`: empty.

### 8.7 Root Utility Scripts

- `init_db.py`: useful for dev bootstrap.
- `inspect_db.py`, `drop_users_table.py`, `recreate_db.py`: ad-hoc maintenance scripts with hardcoded local DB URLs.

## 9. Files in Root That Are Not Necessary (or Should Be Moved/Removed)

Inside `SkuPhase/` root:

High priority cleanup:
- `pyproject.toml` (empty): remove or populate properly.
- `.gitignore` (empty): replace with real ignore rules.

Likely obsolete / duplicate docs:
- `PROJECT_ANALYSIS_SUMMARY.md` (outdated and contradictory).
- `IMPLEMENTATION_STATUS.md` (outdated snapshots).
- `QUICK_REFERENCE.md` (contains unimplemented endpoints and duplicated architecture claims).

Should move to `scripts/maintenance/` if kept:
- `inspect_db.py`
- `drop_users_table.py`
- `recreate_db.py`

Keep:
- `README.md` (but rewrite to match actual routes/features)
- `requirements.txt`
- `.env.example`
- `init_db.py`

## 10. Suggested Features Aligned to Real Problem (Exam Generation, Not Full SIS)

Priority features schools actually need in this product scope:

1. Curriculum coverage report per generated exam
- Show which uploaded document sections were used and which syllabus topics were missed.

2. Marking-scheme quality guardrail
- Validate that each non-MCQ question has explicit rubric points and consistent marks sum.

3. Teacher review workflow (lightweight)
- Draft -> needs_edits -> approved with reviewer and timestamp.

4. Regenerate selected questions only
- Partial regeneration using original context + teacher feedback (already hinted by schemas).

5. Version history for exams
- Keep versions when refined/regenerated; allow rollback.

6. Citation panel for each question
- Link question to source chunks/documents for trust and auditability.

7. Subject/grade templates
- Reusable section patterns (e.g., WAEC-like theory layout per subject).

8. Cost and usage transparency per exam
- Tokens/cost/time metadata visible to admins.

9. Batch document processing queue reliability
- Retries, status transitions, and dead-letter handling.

10. Quality evaluation hooks
- Rule-based checks before publishing (duplicate questions, mark mismatch, too-hard vocabulary).

## 11. What Is Not Necessary Right Now

To avoid scope drift before hardening core value:

- Full school management suite (attendance, fees, timetable, parent portal).
- Complex Stripe/billing UI before generation quality and trust are stable.
- Advanced analytics dashboards before baseline reliability metrics exist.
- Multi-provider optimization logic beyond one primary + one fallback.

## 12. Recommended Immediate Actions (Order)

1. Fix correctness blockers (routes, refresh flow, user self-check bug, regeneration delete bug, document-id-scoped retrieval).
2. Normalize status enums and schema typing mismatches.
3. Add real tests for auth, documents, exam generation happy + failure paths.
4. Consolidate docs to one truthful roadmap/status source.
5. Remove/move unnecessary root files and fill missing project hygiene files.

## 13. Final Assessment

SkuPhase has strong foundational intent and enough implemented components to become production-capable, but currently suffers from prototype drift: critical path bugs, empty stubs, and documentation inconsistency.

The fastest path forward is stabilization, not expansion.
