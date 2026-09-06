# SkuPhase Implementation Plan (Stabilize -> Ship)

Date: 2026-02-28
Input: Code audit from `DETAILED_ARCHITECTURE_ANALYSIS.md`
Goal: Turn current prototype into a reliable exam-generation backend for schools, without scope drift into full school management.

## Implementation Status (Updated: 2026-03-02)

Completed:
- Milestone 0: repo hygiene baseline completed (`pyproject.toml`, `.gitignore`, README setup alignment).
- Milestone 1: critical correctness blockers fixed (auth path duplication, refresh-token dependency, user self-check bug, regeneration cleanup, document-scoped retrieval).
- Milestone 2: data/security consistency fixes completed (JWT config centralization, sensitive log removal, status/type cleanup, count query fixes, pydantic v2 migration).
- Milestone 3: RAG baseline completed (vector-first delegation, embedding dimension checks, retrieval telemetry).
- Milestone 4: core workflow completed (refine endpoint/service, refinement history table + migration, approve endpoint, PDF export endpoint/service).
- Milestone 5: core tests added and endpoint tests expanded; CI workflow added with `pytest` gate.
- Milestone 6: request ID + structured request logs, operations endpoints (`/api/v1/ops/health`, `/api/v1/ops/stats`), and runbook/playbook docs added.
- Milestone 7: teacher/auditor review workflow added (audit comments, admin batched refine-from-comments endpoint, auditor role enablement, proposal queue with admin-only generate-from-proposal).
- Milestone 8: teacher exam authorship flow enabled (proposal package submission + manual exam submission endpoints, teacher review/final submission endpoints).
- Milestone 9: governance-first workflow enforced (admin-only LLM calls, exam-level LLM call budget max=3, teacher final submission gate before admin approval).
- Milestone 10: LLM quality hardening added (single-call internal plan/critique prompt protocol + deterministic post-generation quality validator before persistence).
- Milestone 11: exam quality analytics added (coverage scorer + quality flagging endpoint for teacher/admin review).
- Milestone 12: quality intelligence persistence added (traffic-light scoring + stored quality snapshot history per exam).
- Milestone 13: Question Bank v1 added (save from past exam, browse/filter, manual edit and reuse without AI call).

Remaining:
- Expand CI gates beyond `pytest` when technical debt is reduced (optional hardening track).

## 1. Delivery Strategy

Use 3 tracks in sequence:

- Track A: Correctness and architecture stabilization
- Track B: Core product completion (document -> generate -> refine -> export)
- Track C: Operational hardening and controlled rollout

Do not start net-new major features until Track A is complete.

## 2. Milestones and Timeline

## Milestone 0 (Day 0-2): Repo Hygiene and Truth Alignment

Outputs:
- Single source of truth docs
- Clean root structure
- Working local bootstrap

Tasks:
1. Replace empty `pyproject.toml` with valid project metadata and tool config.
2. Populate `.gitignore` for Python/FastAPI artifacts and local uploads/env files.
3. Move maintenance scripts to `scripts/maintenance/`.
4. Archive or delete stale docs (`PROJECT_ANALYSIS_SUMMARY.md`, `IMPLEMENTATION_STATUS.md`, `QUICK_REFERENCE.md`) after migration of valid content.
5. Update `README.md` with verified endpoints and setup only.

Acceptance:
- No contradictory docs in root.
- New developer can run app from README steps.

## Milestone 1 (Day 3-7): Correctness Blockers (Must-Fix)

Outputs:
- Critical auth and exam bugs fixed
- Endpoint paths match docs

Tasks:
1. Fix auth route definitions:
- Change `auth_router` paths from `/auth/*` to `/*` because prefix already includes `/api/v1/auth`.

2. Fix refresh-token flow:
- Add dedicated dependency for refresh token validation (`token_type == refresh`).
- Keep access-token dependency for protected endpoints.

3. Fix user self-protection bug:
- Replace `current_user.id` with `current_user.user_id` in users router.

4. Fix regeneration cleanup bug in exam generator:
- Replace invalid `select(...).execution_options(...)` with real `delete(Question).where(Question.exam_id == exam_id)`.

5. Enforce document-scoped retrieval in exam generation:
- Filter RAG search results by `request.document_ids`.

6. Normalize document processing statuses:
- Pick one enum set (recommended: `pending`, `in_progress`, `completed`, `failed`) and apply everywhere.

Acceptance:
- API route map exactly matches docs.
- Refresh token endpoint works only with refresh tokens.
- Regeneration does not duplicate stale questions.
- Exam generation only uses teacher-selected docs.

## Milestone 2 (Week 2): Data and Type Consistency

Outputs:
- Stable schemas and model contracts
- Cleaner service boundaries

Tasks:
1. Remove manual UUID string casting in school service responses.
2. Introduce shared enums/constants for statuses and roles.
3. Replace heavy count queries with SQL `COUNT(*)` patterns.
4. Remove sensitive logging (password content).
5. Unify JWT settings usage under `app/config/settings.py` (remove insecure default secret fallback).
6. Ensure model imports happen before `create_all` in dev init path or move fully to migrations.

Acceptance:
- No runtime validation mismatches from UUID/string casting.
- No plaintext password or equivalent sensitive logs.

## Milestone 3 (Week 3): RAG Quality Baseline

Outputs:
- Real semantic retrieval behavior in production path

Tasks:
1. Make `DocumentService.search_chunks` delegate to `RAGService.search`.
2. Add embedding-dimension compatibility checks (`Vector(384)` with local model; reject mismatched vectors).
3. Add fallback strategy:
- Vector retrieval first
- Text fallback only when embeddings unavailable
4. Add retrieval quality telemetry (top_k, similarity scores, source docs).

Acceptance:
- Search endpoint returns ranked semantic matches when embeddings exist.
- Exam context quality improves and is explainable.

## Milestone 4 (Week 4): Feature Completion for Core Workflow

Outputs:
- Complete teacher loop: generate -> review -> refine -> approve

Tasks:
1. Implement refine endpoint and service (`/exams/{id}/refine`).
2. Add exam versioning or refinement history table.
3. Add lightweight approval endpoint with status transition checks.
4. Implement export service MVP (PDF first, DOCX second).

Acceptance:
- Teacher can refine selected questions and keep history.
- Export works for approved exams with stable formatting.

## Milestone 5 (Week 5): Test Coverage and CI Gate

Outputs:
- Automated safety net for regressions

Tasks:
1. Add tests (currently missing):
- `tests/test_auth.py` (register, login, refresh, me)
- `tests/test_exam_generation.py` (success, bad docs, parse failure)
- `tests/test_refinement.py` (feedback mapping, partial regen)
- documents processing and status transitions
2. Add integration tests for tenant isolation.
3. Add lint/type checks in CI.

Acceptance:
- Minimum target: 70% service-layer coverage on critical modules.
- CI blocks merges on failing tests.

## Milestone 6 (Week 6): Controlled Rollout Readiness

Outputs:
- Operational confidence for pilot schools

Tasks:
1. Add structured logging and request IDs.
2. Add usage logging per generation/refinement/export action.
3. Add admin observability endpoints (basic health + queue stats).
4. Add backup/recovery playbook and incident runbook.

Acceptance:
- Pilot environment can trace exam generation failures end-to-end.

## 3. Work Breakdown by File

High-priority files for immediate edits:
- `app/api/v1/auth_router.py`
- `app/core/dependencies.py`
- `app/api/v1/users_router.py`
- `app/services/exam_generator.py`
- `app/services/document_service.py`
- `app/services/rag_service.py`
- `app/core/security.py`
- `app/models/document.py`
- `README.md`

Secondary files:
- `app/schemas/school.py`
- `app/services/school_service.py`
- `tests/test_auth.py`
- `tests/test_exam_generation.py`
- `tests/test_refinement.py`

## 4. Prioritized Backlog (P0/P1/P2)

P0 (blockers):
1. Auth path fix
2. Refresh token correctness
3. User self-check bug
4. Regeneration delete fix
5. Document-scoped retrieval

P1 (quality-critical):
1. Enum/status normalization
2. Sensitive log removal
3. Real semantic search in primary service path
4. Missing test suite for core flows

P2 (value-add after stability):
1. Refinement history/versioning
2. Export improvements
3. Usage/cost dashboards

## 5. Out of Scope Until Stability

- General school ERP features (attendance, fees, parent portal).
- Advanced billing automation and invoice UI.
- Complex multi-provider model routing optimization.

## 6. Definition of Done for "Production Candidate"

SkuPhase can be considered production-candidate when:

1. Tenant isolation is enforced and tested on all data paths.
2. Generate/refine/export flows are functional and covered by automated tests.
3. Docs match actual routes and behavior.
4. No critical auth/token bugs remain.
5. RAG retrieval is semantic for embedded documents and auditable via citations.

## 7. Suggested Execution Order for Our Next Sessions

1. Session 1: P0 bug fixes + route normalization.
2. Session 2: status/type/security cleanup + doc corrections.
3. Session 3: test suite completion for auth/documents/exams.
4. Session 4: refinement endpoint + history + approval flow.
5. Session 5: export MVP + rollout hardening.
