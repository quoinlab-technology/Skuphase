# SkuPhase Audit Remediation Plan

**Source**: Principal audit of 2026-08-25 (67 API ops, 9 routers, 13 services, 11 migrations reviewed; pytest 42/50 passing).
**Status**: DRAFT ΓÇö awaiting owner approval before any code changes.
**Rule**: No finding is left unresolved. Every audit finding ID maps to exactly one work package below.

---

## 0. Owner Decisions Locked In (2026-08-25)

| # | Decision | Consequence for this plan |
|---|----------|---------------------------|
| D1 | Launch **Primary first** (Pre-Nursery ΓÇô Primary 6); source JSS/SSS data later | WP4.5 scope guards; no secondary data work |
| D2 | **Scrap schoolΓåÆplatform sharing entirely**. If content is ever shared, it is uploaded to the server and the owner curates/embeds it **manually, outside the server** | `owner_type='school'` on all teacher saves; platform corpus seeded only by owner-run scripts; zero ML on server |
| D3 | Past-question strategy: leaning **rephrase** ΓÇö see ┬º1 recommendation | Affects question-bank ingestion policy only, not code |
| D4 | Email via **Resend** | WP1.1 mailer |
| D5 | Serve **both** individual teachers and school admins | WP4.4 dual-mode permissions |
| D6 | Payments later via **Paystack or Flutterwave** | Billing stays out of scope; schema made billing-ready (WP3.2) |
| D7 | Stay on **Supabase free tier** for now; monitor against pausing | WP4.6 keep-alive + optional backup cron |
| D8 | **Embeddings and RAG completely removed from the server** | WP2.1 deletions |
| D9 | **Gmail SMTP for MVP email**; Resend account started separately, switch when ready | WP1.1 mailer built as provider abstraction (`MAIL_PROVIDER=smtp|resend`); SMTP default |
| D10 | Documents + Assets subsystem **deleted entirely** (CP1 approved) | WP2.2 Option A proceeds |
| D11 | Dev database is **disposable ΓÇö drop & re-seed** (CP2 approved) | WP3.2 migration squash strategy (i) |
| D12 | Rename `GROK_*` ΓåÆ `GROQ_*` everywhere (CP8 approved) | WP2.3 settings + WP5.2 docs |

---

## 0b. Step 0 ΓÇö Safety Baseline (MANDATORY FIRST)

This directory is **not a git repository**. Every deletion and edit in this plan would be permanent.

1. `git init` in `skuphase/`, add a proper `.gitignore` (.env, uploads/, exports/, __pycache__, caches, venv).
2. Initial commit of current state = restore point for every subsequent phase.
3. Verify `.env` is ignored BEFORE committing (it contains live secrets).

Effort: 0.25 d. Nothing else starts until this commit exists.

---

## 1. Recommendation on Past Questions (answer to Q3)

**Do not build a systematic WAEC/NECO paraphrase pipeline.** Paraphrasing reduces verbatim-copy risk but a wholesale rewording of protected exam papers is still derivative work, and examination bodies actively enforce their copyright. The safer and cheaper v1 posture:

1. **Original generation is already the product**: the generator creates brand-new items aligned to scheme-of-work objectives ΓÇö nothing to infringe. Lean into that.
2. **Few-shot examples from safe sources**: NERDC teacher guides publish sample assessment items (government works, low risk) and teachers can contribute their own items under the ToS. Curate these manually into the platform bank (per D2) with an admin script.
3. **If you ever ingest real past papers**: keep them private (never redistributed through the API), use them only as offline style references, store topic/metadata tags in the shared corpus rather than verbatim text.

Net: same engineering cost as a paraphrase pipeline (zero), materially lower legal exposure. The few-shot selector works identically either way ΓÇö it just needs *some* curated rows.

---

## 2. Phase Overview & Timeline

| Phase | Theme | Work packages | Effort |
|-------|-------|---------------|--------|
| **Step 0** | Safety baseline: git init + restore-point commit (┬º0b) | ΓÇö | ~0.25 d |
| 1 | P0 security & correctness (no schema changes) | WP1.1ΓÇôWP1.5 | ~3.5 d |
| 2 | Removals & hygiene (D2/D8/D10) | WP2.1ΓÇôWP2.3 | ~3.5 d |
| 3 | Data layer (single migration event, D11 disposable re-seed) | WP3.1ΓÇôWP3.3 | ~3 d |
| 4 | Platform enablement | WP4.1ΓÇôWP4.6 | ~5.5 d |
| 5 | Verification & docs | WP5.1ΓÇôWP5.2 | ~3.5 d |
| | | **Total** | **~19 dev-days Γëê 4 weeks solo** |

Ordering rationale: schema-affecting fixes (tenant CHECK, nullable plan_id, dropped tables) are folded into ONE new baseline migration in Phase 3 so we never migrate twice. Phase 1 items are pure code and shippable immediately.

---

## Phase 1 ΓÇö P0 Security & Correctness

### WP1.1 Password-reset / verification token leak + email delivery
**Fixes**: A1 (P0), F1 (P2), D9.
**Files**: `app/services/auth_service.py`, `app/services/user_service.py`, new `app/services/mailer.py`, new `app/utils/` email templates, `app/config/settings.py`.

Changes:
1. `request_password_reset` (auth_service.py:350ΓÇô367): remove `"reset_token": reset_token` from the return dict. Response body becomes generic message only, for both known and unknown emails.
2. `resend_verification` (auth_service.py:415ΓÇô433): remove `"verification_token": token` from response.
3. New `mailer.py` ΓÇö **provider abstraction**, switchable by env (`MAIL_PROVIDER=smtp|resend`, default `smtp`):
   - `SMTPMailer`: async send via `aiosmtplib` over Gmail (`smtp.gmail.com:587`, STARTTLS) using a Gmail **App Password**. MVP limits to note in README: ~500 sends/day, deliverability is best-effort.
   - `ResendMailer`: same interface via Resend HTTP API (httpx) ΓÇö implemented now, activated later by flipping one env var when the domain is verified. No code change needed at cutover.
   - Both implement `async def send_email(to, subject, html)`; simple HTML templates (reset, verify, invite) as Python f-string builders in `app/utils/email_templates.py` ΓÇö no template engine dependency.
   - If mail is unconfigured ΓåÆ log the action link at WARNING (server logs only, never HTTP responses) so dev flow still works.
4. Wire emails: forgot-password (reset link `{app_base_url}/reset-password?token=ΓÇª`), resend-verification, `invite_user` (user_service.py:73ΓÇô79 currently returns `invite_token` ΓåÆ email the invited teacher the accept-invite link instead; response keeps metadata minus raw token).
5. Settings additions: `mail_provider: str = "smtp"`, `smtp_host/smtp_port/smtp_user/smtp_password`, `resend_api_key: str = ""` (dormant until used), `mail_from`, `app_base_url`.
6. New dev dependency: `aiosmtplib`. Owner action before production use: enable 2FA on the sender Gmail account and generate an App Password.

Acceptance:
- `POST /auth/forgot-password` response contains no token field (test asserts).
- With SMTP creds unset, link appears in logs; with test App Password set, real inbox receives mail.
- Invite flow delivers accept link by email.
- Flipping `MAIL_PROVIDER=resend` + key routes through Resend with zero code changes.

Effort: 1 d.

### WP1.2 Question-bank tenant-leak fix (code side)
**Fixes**: A2 (P0) code half; DB CHECK lands in WP3.2.
**Files**: `app/api/v1/exams_router.py`, `app/models/question_bank.py`, `app/schemas/exam.py`.

Changes:
1. `save_exam_questions_to_bank` (exams_router.py:814ΓÇô833): set `owner_type="school"` explicitly on every created item.
2. Remove Python default `default="platform"` from `QuestionBankItem.owner_type` (question_bank.py:27) ΓÇö every creation site must state intent explicitly. Future manual platform ingestion script sets `'platform'` explicitly (WP3.3 companion script).
3. Align `QuestionBankItemResponse.owner_type` default (schemas/exam.py:432) or drop the default.

Acceptance:
- Regression test: School A saves bank items ΓåÆ run `FewShotSelector.select` ΓåÆ none of A's items returned (selector reads `owner_type='platform'` only).
- Grep proof: no creation path leaves owner_type implicit.

Effort: 0.5 d.

### WP1.3 Upload hardening (path traversal + size streaming)
**Fixes**: A4 (P0), H10 (P3).
**Files**: `app/api/v1/documents_router.py`, `app/api/v1/assets_router.py`, new `app/utils/uploads.py`, `app/config/settings.py`.

Changes:
1. New `uploads.py::store_upload(upload_file, dest_dir, allowed_exts, max_mb)`:
   - Filename replaced with `uuid4().hex + validated_ext`; original name kept only as metadata.
   - Magic-byte sniffing (%PDF, \x89PNG, \xff\xd8\xff) must match extension; else 400.
   - Streams to disk in 1 MiB chunks; aborts + deletes partial when exceeding `settings.max_file_size_mb`.
2. Use in `upload_document` (documents_router.py:93ΓÇô130) and `upload_asset` (assets_router.py:94ΓÇô103). Allowed: pdf/png/jpg/jpeg/webp per endpoint context.
3. Wire `max_file_size_mb` setting (raise default to 50 to match current behavior); delete hardcoded `50 * 1024 * 1024`.

Acceptance:
- Tests: `../../.env` filename, double-extension spoof, MIME-header mismatch, oversize stream ΓÇö all rejected; stored tree contains only UUID names.

Effort: 1 d.

### WP1.4 Exam governance bypass closure
**Fixes**: C3 (P1).
**Files**: `app/schemas/exam.py`, `app/api/v1/exams_router.py`.

Changes:
1. `ExamUpdateRequest.status` validator (schemas/exam.py:149ΓÇô156): allowed set shrinks to `{"draft", "under_review"}`. `"approved"` unreachable via PUT.
2. `update_exam` (exams_router.py:1448+): if `exam.workflow_state == "approved"`, reject any mutation with 409 (approved exams immutable).
3. Introduce single transition map constant (generation_requested ΓåÆ teacher_review ΓåÆ final_submitted_by_teacher ΓåÆ approved; refinement_requested ΓåÆ teacher_review) in one module and reference it from approve/submit-final/refine endpoints so illegal transitions are impossible to reintroduce.

Acceptance: `PUT /exams/{id}` with `status=approved` ΓåÆ 422; mutating an approved exam ΓåÆ 409; existing workflow tests updated.

Effort: 0.5 d.

### WP1.5 Small security fixes
**Fixes**: F2 (P2), F3 (P2).
**Files**: `app/api/v1/users_router.py`, `app/api/v1/ops_router.py`.

1. `GET /users/` (users_router.py:56): add `require_school_admin`.
2. `ops_health` (ops_router.py:31ΓÇô32): raise 503 with generic `detail="database_unhealthy"` (no exception text). Keep `/stats` gated as-is.

Effort: 0.25 d.

---

## Phase 2 ΓÇö Removals & Hygiene (implements D2/D8)

### WP2.1 Delete the ML stack
**Fixes**: B1 (P1), B2 (P1), D1 (P1), H4 (P3), E3 (P2, deleted outright).

Deletions (files removed):
- `app/services/embedding_service.py`
- `app/services/rag_service.py`
- `app/services/document_processor.py`
- `app/api/v1/rag_router.py`
- `tests/test_documents.py` processing tests (rewritten per fate decision below)

Code edits:
- `main.py`: drop rag_router import/include (lines 12ΓÇô22, 110).
- `exam_generator.py`: `__init__` loses EmbeddingService/RAGService entirely; `retrieve_context` keeps (1) scheme-of-work objectives and (2) few-shot selection only; document-chunk branch and `chunks` key removed; fallback line 241ΓÇô242 retained; validator metric `rag_chunks_used` dropped.
- `requirements.txt` removals: sentence-transformers, torch, numpy (verify last consumer gone), paddleocr, paddlepaddle, pytesseract, opencv-python-headless, PyPDF2, tiktoken, weasyprint, pillow*(verify reportlab need)*, python-docx, svglib, python-fasthtml, anthropic, sentry-sdk, structlog, python-json-logger, gunicorn (replace with documented `uvicorn --workers` guidance), faker/factory-boy (verify unused in tests first).
- `database.py init_db`: remove `CREATE EXTENSION IF NOT EXISTS vector` block (lines 54ΓÇô60).

Acceptance: `pip install -r requirements.txt` on clean venv; app imports; image/RAM footprint drops (~torch+paddle gone); grep shows zero references to removed modules.

Effort: 1 d.

### WP2.2 Documents & Assets subsystem removal ΓÇö Γ£à APPROVED (CP1/D10)
**Context**: With RAG/embeddings gone (D8), the document pipeline has no consumer: generation accepts empty `document_ids`, proposals are optional-by-design, chunks/embeddings tables would be dead weight. Assets exist to feed prompt-side figure references + export images ΓÇö also unused without pilots.

**Proceeding with Option A (remove now, restore cleanly later)**:
- Delete: `documents_router.py`, `rag_router.py` (already), `assets_router.py`, `document_service.py`, models `SchoolDocument`, `DocumentChunk`, `DocumentVisualRef`, `LearningAsset`, `QuestionAssetRef`, `ExamContext`; schemas document.py/asset.py; router registrations; `uploads/documents` handling.
- Simplify consumers: `ExamGenerationRequest.document_ids/asset_ids` removed; proposal `document_ids` removed (schemas/exam.py:75ΓÇô82, 326ΓÇô329; exams_router doc-validation loops at 537ΓÇô550, 944ΓÇô956, 1041ΓÇô1053 disappear ΓÇö this also resolves those N+1 loops); `_validate_and_fetch_assets` / `_fetch_question_asset_map` / `_build_export_asset_payload` / asset sections of `_run_exam_preflight` deleted; `store_exam` ExamContext block removed; export asset-image blocks removed (WP4.1 builds text-only).
- Tables dropped in the WP3.2 baseline (dev DB will be dropped & re-seeded per CP2/D11, so no data migration needed).
- Future re-introduction = fresh small module (upload-to-storage only, embeddings run offline by owner per D2).

Effort: 1 d incl. consumer surgery.

### WP2.3 Hygiene sweep
**Fixes**: H1, H2, H3, H5, H6, H7, H12, E1, E2(code note), E4, E6, G2.

1. **H1 stubs**: DELETE zero-byte files: `services/usage_limiter.py`, `services/question_manager.py`, `core/limits.py`, `models/settings.py`, `models/subscription.py`, `prompts/exam_generation.py`, `prompts/refinement.py`, `schemas/question.py`, `utils/context_manager.py`, `utils/error_handlers.py`, `utils/validation.py`. EXCEPTION: implement `core/permissions.py` properly (role-set dependency factory ΓÇö used by WP1.5/WP4.4).
2. **H2 settings**: prune unread fields (`supabase_*`, `google_*`, `api_prefix`, `openai_embedding_api_key`). START reading: `database_pool_size/max_overflow` (WP3.1), `refresh_token_expire_days` (login auth_service.py:286 + refresh :338 replace hardcoded `days=30`), `max_file_size_mb` (WP1.3). Additions from WP1.1.
3. **H3 config parsing**: add `mode="before"` validators splitting comma-separated strings for `cors_origins`/`cors_methods`; fix `.env.example` (`postgresql+asyncpg://ΓÇª`, CORS format note, Resend vars, remove Supabase/Google blocks). Live `.env` already uses JSON arrays ΓÇö validator accepts both.
4. **H5**: exams_router.py:601 `request.dict()` ΓåÆ `request.model_dump(mode="json")`.
5. **H6**: curriculum schemas class-based `Config` ΓåÆ `model_config = ConfigDict(...)` (kills the 3 deprecation warnings seen in pytest output).
6. **H7**: remove `enable_katex` + `bloom_distribution` (unused). KEEP `difficulty_distribution` and make it real: inject a difficulty-mix instruction paragraph in `build_prompt` so the validator's check (exam_quality_validator.py:177ΓÇô187) actually has something enforcing it. *(CP5: say the word if you'd rather drop it too.)*
7. **H12**: delete `pages/`, root scripts `recreate_db.py`, `drop_users_table.py`, `inspect_db.py`, root `app.py` (verify redundant vs run_server.py first), stale docs `ASSET_FORMULA_RENDERING_PLAN.md`, `BACKEND_ASSET_IMPLEMENTATION_STATUS.md`, `DETAILED_ARCHITECTURE_ANALYSIS.md`, `IMPLEMENTATION_PLAN_WORKAROUND.md`. *(CP6 pending ΓÇö all recoverable via Step 0 baseline once approved)*
8. **D12 / CP8**: rename settings `grok_api_key`ΓåÆ`groq_api_key`, `grok_base_url`ΓåÆ`groq_base_url`; rename env vars `GROK_*`ΓåÆ`GROQ_*`; fix "Grok" misnomers in llm.py docstrings/logs (llm.py:20ΓÇô47). Update `.env.example`; owner updates local `.env` once.
9. **E1**: `list_exams` question counts via one grouped subquery join instead of per-exam COUNT loop (exams_router.py:1195ΓÇô1212).
10. **E4**: refine-from-comments validates open comments BEFORE `_consume_llm_call_budget` (move block exams_router.py:1872 after 1887 check).
11. **G2**: `QuestionResponse.sub_parts` type loosened to `Optional[List[dict]]` (schemas/exam.py:189) ΓÇö generated exams can no longer 500 on loose LLM dicts; `ManualQuestionInput` keeps strict input validation.
12. **E6**: moot under Option A (CP1 approved).
13. **E2**: code unchanged; proper matching indexes added in WP3.2 (functional index on `lower(subject), lower(grade_level)`).

Acceptance: ruff clean (no unused imports), app boots, OpenAPI diff reviewed, all existing tests adjusted.

Effort: 1.5 d.

---

## Phase 3 ΓÇö Data Layer (one migration event)

### WP3.1 Engine pooling + session discipline around LLM calls
**Fixes**: C1 (P1).
**Files**: `app/core/database.py`, `app/services/exam_generator.py`, `app/api/v1/exams_router.py`.

1. Replace NullPool (database.py:21ΓÇô25) with defaults pool: `pool_size=settings.database_pool_size`, `max_overflow=settings.database_max_overflow`, `pool_pre_ping=True`, `pool_recycle=1800`. (We deploy long-lived VPS/container, not serverless.)
2. Session discipline: no open transaction across LLM awaits.
   - `ExamGenerator.generate_exam` refactored to take a session factory: Stage 1 short session (retrieve curriculum + few-shot) ΓåÆ close; LLM call sessionless; Stage 2 short session (validateΓåÆstore_exam commit).
   - Refine paths (router-driven): split `refine_exam` into `prepare_refinement(db)` (fetch questions/comments, build payload) + `apply_refinements(db, ΓÇª)`; router opens session 1 ΓåÆ prepare ΓåÆ close ΓåÆ LLM ΓåÆ session 2 ΓåÆ apply.
3. Acceptance: staging check ΓÇö during an artificially slow LLM call, `pg_stat_activity` shows no `idle in transaction` session for the request; concurrent-generation soak (10├ù) holds Γëñ pool-size connections.

Effort: 1 d.

### WP3.2 Migration re-baseline ΓÇö Γ£à disposable re-seed (CP2/D11)
**Fixes**: A7 (P0), plus schema deltas: A2 CHECK constraint, A3 nullable plan_id, E2 functional indexes, WP2.x table drops.

1. Prune models first (Phase 2 done), then generate ONE new `0001_initial_schema` via autogenerate on an empty database, hand-edited to add:
   - `CHECK ((owner_type='platform' AND school_id IS NULL) OR (owner_type='school' AND school_id IS NOT NULL))` on question_bank_items;
   - `school_subscriptions.plan_id` ΓåÆ NULLABLE (NULL = unmanaged/free ΓÇö billing-ready for Paystack later);
   - Functional index `ix_qb_platform_lookup ON question_bank_items (lower(subject), lower(grade_level), week_index) WHERE owner_type='platform' AND is_active` (fixes E2 seq-scans);
   - Covering index `ix_exams_school_created ON exams (school_id, created_at)` (rate-limit COUNT, H8);
   - `users.token_valid_after timestamptz NULL` (WP4.3);
   - Jobs table (WP4.2).
2. Delete migrations 0002ΓÇô0011 (chain squashed). `env.py` unchanged.
3. Dev DB disposition per D11: **drop database ΓåÆ fresh `alembic upgrade head` ΓåÆ re-run curriculum seeder**. Old uploads/exports on disk are disposable; one-time data fix unnecessary on a clean slate.
4. Drill: scratch Postgres (docker `postgres:16`), `alembic upgrade head` twice (idempotent), `downgrade base` round-trip, `init_db` gate passes.

Effort: 1.25 d.

### WP3.3 Seeder + platform-corpus ingestion script
**Fixes**: H9 (P3), supports D2.

1. `seed_curriculum_postgres.py`: bulk upserts ΓÇö curriculums via `on_conflict_do_update(constraint ix_curriculums_lookup)`, schemes via `on_conflict_do_update(constraint ix_scheme_lookup)`; eliminates 3,081 per-row SELECTs and per-row flushes.
2. Input path: relative default `data/nerdc_scheme_database.final.json`; copy the normalized dataset into the repo (Γëê3k rows, a few MB) so seeding is reproducible anywhere. *(CP3 pending)*
3. New `app/scripts/ingest_platform_questions.py` (admin-only, run locally): takes curated JSON/CSV of past-question items ΓåÆ inserts `question_bank_items` with `owner_type='platform'`, `school_id=NULL`, canonical lowercase subject/grade, week_index, exam_type/source_year. This replaces auto-sharing with deliberate curation (D2). Source policy per CP4/┬º1.

Effort: 0.5 d.

---

## Phase 4 ΓÇö Platform Enablement

### WP4.1 Export rebuild + download endpoint
**Fixes**: A5 (P0), A6 (P0).

1. Rewrite `export_service.py` on ReportLab **platypus**: `Paragraph` styles for meta/instructions/questions/options/marking-scheme; full word-wrap everywhere (no more `text[:120]` truncation); page numbers in footer; answer-key variant appends Answers section; fenced markdown blocks rendered as monospace blocks; Mermaid blocks rendered as caption placeholder `[diagram: <first line>]` (documented limitation ΓÇö true diagram rendering deferred); `$ΓÇª$` math passed through literally until frontend/KaTeX-PDF story exists.
2. Storage layout: `exports/{school_id}/{exam_id}/{uuid}.pdf` (local disk fine for single instance; path abstraction ready for object storage later).
3. New endpoints: `GET /api/v1/exams/{exam_id}/exports` (list) and `GET /api/v1/exams/{exam_id}/exports/{filename}` ΓåÆ FileResponse, filename regex-validated `[0-9a-f]{32}\.pdf`, exam ownership checked. `POST ΓÇª/export` response gains `download_url` and stops returning bare server paths.
4. Build runs via `run_in_executor` (keeps event loop snappy).

Acceptance: pypdf text-extraction test asserts a 300-char question appears complete; cross-school download ΓåÆ 404; wrap visual check.

Effort: 2 d.

### WP4.2 Durable job queue (Postgres-backed, no broker)
**Fixes**: C2 (P1), E5 (P2).

1. `jobs` table (created in WP3.2): id, kind, payload JSONB, status(pending/running/succeeded/failed), attempts, max_attempts, last_error, run_at, timestamps, exam_id.
2. Worker: asyncio task started in lifespan; poll loop (2 s): `SELECT ΓÇª WHERE status='pending' AND run_at<=now() ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 5`.
3. Error classification: provider timeouts / 429 / 5xx = transient ΓåÆ exponential backoff re-queue (attempts<3); parse/validation failures (ValueError from parse_response/quality_validator) = permanent ΓåÆ job failed, exam.status='failed', failure_reason persisted. Kills the 3├ù LLM burn on deterministic failures (E5) while keeping restart-survivable retries (C2).
4. Stale-run reaper: `running` rows older than 10 min ΓåÆ back to pending (single-worker assumption documented; SKIP LOCKED makes multi-instance safe anyway).
5. `/generate` and `/generate-proposals/{id}/generate` enqueue jobs instead of `background_tasks.add_task`; BackgroundTasks usage eliminated.

Effort: 1.5 d.

### WP4.3 Auth hardening
**Fixes**: F4 (P2 remainder).

1. Login throttling: sliding-window counter keyed `(email_norm, ip)` ΓÇö 5 failed attempts ΓåÆ 15-min lockout; generic 401 always. In-memory dict acceptable for single instance (documented limitation).
2. Credential-change invalidation: `token_valid_after` (column from WP3.2) bumped on reset_password + accept_invitation; `get_current_user` / refresh dependency compare JWT `iat >= token_valid_after` ΓåÆ old tokens die on password change.
3. `expires_in` derived from `ACCESS_TOKEN_EXPIRE_MINUTES*60` instead of hardcoded 3600 (auth_service.py:292,344).

Effort: 1 d.

### WP4.4 Dual-mode access (individual teachers Γçä schools)
**Fixes**: D5; formalizes scattered role logic (audit Track E duplicate-permission note).

1. `core/permissions.py`: `allows_llm_actions(user) := role=='school_admin' or account_type=='individual_teacher'`; `require_roles(*roles)` FastAPI dependency factory; `require_llm_permission()` dependency.
2. Replace inline checks at exams_router generate (:530), refine (:1778), refine-from-comments (:1854), approve (:1964), export (:2051), delete (:2165), documents/assets remnants, with the dependencies. Individual teachers get instant generate/self-approve inside their personal workspace; school staff keep proposalΓåÆadmin governance untouched.
3. Permission matrix table added to README.

Effort: 0.5 d.

### WP4.5 Primary-first scope guards
**Fixes**: G1 (P1 product decision).

1. Generation/proposal endpoints: when `term`+`selected_weeks` supplied and scheme lookup returns empty ΓåÆ 400 with hint listing available classes (from CurriculumService order map).
2. When weeks omitted or data missing ΓåÆ proceed, but response meta carries warning "No official NERDC scheme data for {class} {subject} {term}; generated from general curriculum".
3. README/OpenAPI copy states coverage: Pre-Nursery ΓÇô Primary 6 (JSS/SSS planned).

Effort: 0.5 d.

### WP4.6 Free-tier uptime & safety net
**Fixes**: D7.

1. `.github/workflows/ping.yml`: cron every 2 days ΓåÆ GET `https://{host}/api/v1/ops/health` (touches DB ΓåÆ resets Supabase idle timer; host from repo variable).
2. Optional (recommended): weekly scheduled `pg_dump` via GitHub Action to private storage ΓÇö free tier has no PITR; losing school data to a paused/deleted project is the real tail risk.
3. Watch-item: 500 MB free DB ceiling noted in README ops section.

Effort: 0.25 d.

---

## Phase 5 ΓÇö Verification & Documentation

### WP5.1 Test-suite overhaul
**Fixes**: closes the 8 known failures; covers every fix above.

1. Fix stale tests:
   - test_exam_generation ├ù2 ΓåÆ update to new `retrieve_context`/`store_exam` signatures (post-WP2 slimming they shrink further).
   - test_exam_generator_v2 rag-failure expectation ΓåÆ align with non-fatal design (now trivially true post-deletion).
   - test_exams_router ├ù4 ΓåÆ replace SimpleNamespace fakes with proper result mocks (`.scalars()` chains) or integration-style tests.
   - test_export_service ΓåÆ install reportlab in dev requirements; assert wrapped content.
2. New coverage:
   - Tenant isolation suite (bank leak regression, cross-school probes on exams/documents-if-kept/users/status changes).
   - Registration happy-paths both modes WITHOUT plan_id (needs PG ΓÇö see CI).
   - Upload abuse pack (traversal/spoof/oversize).
   - Export wrap + download authorization.
   - Job queue success/transient-retry/permanent-fail/reap.
   - Login throttle + token invalidation after reset.
   - Dual-mode permission matrix parametrized test.
3. `requirements-dev.txt` split; `@pytest.mark.integration` marker requiring `TEST_DATABASE_URL`.
4. `.github/workflows/ci.yml`: ruff + pytest unit on push; integration job with `postgres:16` service container. Green CI becomes merge gate.

Effort: 2.5 d.

### WP5.2 Bootstrap drill + docs truth-up
**Fixes**: A7 verification, documentation drift findings (Supabase/OAuth fiction, "Grok" misnomer, stale plans).

1. `docker-compose.yml` (pg16) + `scripts/bootstrap_dev.ps1`: venv ΓåÆ install ΓåÆ .env from example ΓåÆ `init_db` ΓåÆ seed ΓåÆ uvicorn smoke.
2. Rewrite README: architecture-as-built (curriculum-first SQL, no ML on server), corrected env names per D12 (`GROQ_*`), Gmail-SMTP email setup + Resend cutover note, Primary-only coverage, permission matrix, ops runbook (ping/backup/restore).
3. Delete or archive stale docs: `DETAILED_ARCHITECTURE_ANALYSIS.md`, `IMPLEMENTATION_PLAN_WORKAROUND.md`, `BACKEND_ASSET_IMPLEMENTATION_STATUS.md`, `ASSET_FORMULA_RENDERING_PLAN.md` *(CP6: confirm deletion vs archive folder)*. `QUICK_REFERENCE.md` pricing/env sections corrected.

Effort: 1 d.

---

## 3. Findings Coverage Matrix

Every audit ID ΓåÆ owning work package:

| Finding | WP | Finding | WP | Finding | WP | Finding | WP |
|---|---|---|---|---|---|---|---|
| A1 P0 | 1.1 | B1 P1 | 2.1 | E1 P2 | 2.3 | H1 P3 | 2.3 |
| A2 P0 | 1.2+3.2 | B2 P1 | 2.1 | E2 P2 | 3.2 | H2 P2 | 2.3 |
| A3 P0 | 3.2 | C1 P1 | 3.1 | E3 P2 | 2.1 | H3 P2 | 2.3 |
| A4 P0 | 1.3 | C2 P1 | 4.2 | E4 P2 | 2.3 | H4 P3 | 2.1 |
| A5 P0 | 4.1 | C3 P1 | 1.4 | E5 P2 | 4.2 | H5 P3 | 2.3 |
| A6 P0 | 4.1 | D1 P1 | 2.1 | E6 P2 | 2.2/2.3 | H6 P3 | 2.3 |
| A7 P0 | 3.2 | F1 P2 | 1.1 | F2 P2 | 1.5 | H7 P3 | 2.3 |
| G1 P1 | 4.5 | G2 P2 | 2.3 | F3 P2 | 1.5 | F4 P2 | 1.1/4.3 |
| H8 P3 | 3.2 | H9 P3 | 3.3 | H10 P3 | 1.3 | H11 P3 | 2.3* |
| H12 P3 | 2.3 | | | | | | |

\* H11 (unauthenticated curriculum routes): decision = keep public intentionally (marketing-friendly read-only corpus); documented in README. Revisit if abuse appears.

Unresolved count after plan: **0**.

---

## 4. Approval Checkpoints

| CP | Question | Status |
|----|----------|--------|
| CP1 | Documents+Assets subsystem: remove entirely (Option A) or keep dormant (B)? | Γ£à APPROVED ΓÇö Option A (D10) |
| CP2 | Dev DB: disposable re-seed or preserve+stamp? | Γ£à APPROVED ΓÇö disposable re-seed (D11) |
| CP3 | Copy curriculum dataset JSON into repo for reproducible seeding? | ΓÅ│ pending ΓÇö see plain-English ┬º4b |
| CP4 | Past-question stance per ┬º1 (original-gen + curated safe sources, no paraphrase pipeline)? | ΓÅ│ pending ΓÇö see ┬º4b |
| CP5 | `difficulty_distribution`: wire into prompt+validator (kept) or drop? | ΓÅ│ pending ΓÇö see ┬º4b |
| CP6 | Delete stale docs/root scripts/`pages/`? | ΓÅ│ pending ΓÇö see ┬º4b |
| CP7 | Email provider | Γ£à ANSWERED ΓÇö Gmail SMTP now, Resend-ready abstraction (D9) |
| CP8 | Rename GROK_* ΓåÆ GROQ_* env vars | Γ£à APPROVED (D12) |

---

## 4b. CP3ΓÇôCP6 in Plain English (decide each with yes/no)

**CP3 ΓÇö "Copy the data file into the project?"**
The clean curriculum dataset currently lives *outside* the project at
`C:\Users\DELL\Desktop\FastStrap\pdf_process\nerdc_scheme_database.final.json`,
and the seed script has your Desktop path hardcoded inside it. That means nobody
(including future-you on a server) can seed the database without this exact laptop.
CP3 asks: may I **copy that one JSON file into `skuphase/data/`** and point the script
at it? Cost: a few MB in the repo. Benefit: seeding works anywhere, deploys are reproducible.
ΓåÆ Recommend: **Yes.**

**CP4 ΓÇö "How do we handle past-question copyright?"**
This is a policy approval, not a code task. It says: we will NOT copy or reword WAEC/NECO
papers. The AI writes original questions (already does), and you hand-pick a small set of
safe example questions (NERDC teacher-guide samples, teacher-contributed) to seed the
few-shot bank via the admin script from WP3.3.
ΓåÆ Recommend: **Approve as written.**

**CP5 ΓÇö "Keep or delete the difficulty-mix option?"**
Teachers can already send `difficulty_distribution` ("30% easy, 50% medium, 20% hard") in
the generate request. Today it's half-dead: the validator checks it, but the AI never
actually receives it. CP5 asks: keep the field and wire it into the prompt so it genuinely
works, or delete it to keep the API minimal?
ΓåÆ Recommend: **Keep + wire** (validator code already exists; one prompt paragraph).

**CP6 ΓÇö "Delete the leftover junk?"**
Files left over from earlier experiments that no longer match reality:
- `recreate_db.py`, `drop_users_table.py`, `inspect_db.py` ΓÇö dangerous one-off DB scripts (one literally drops the users table!)
- root `app.py` ΓÇö stale entry-point duplicate of `run_server.py`
- 4 outdated docs (`ASSET_FORMULA_RENDERING_PLAN.md`, `BACKEND_ASSET_IMPLEMENTATION_STATUS.md`, `DETAILED_ARCHITECTURE_ANALYSIS.md`, `IMPLEMENTATION_PLAN_WORKAROUND.md`)
- `pages/` ΓÇö contains only an orphaned compiled `.pyc` file, source long gone

With Step 0's git baseline these are all recoverable later if needed.
ΓåÆ Recommend: **Delete all.**

---

## 5. Out of Scope (explicitly deferred)

- Frontend build (separate track once API freezes at end of Phase 4).
- Paystack/Flutterwave billing implementation (schema made ready in WP3.2; build after pilot pricing is settled).
- JSS/SSS curriculum sourcing & ingestion (post-launch data track).
- True diagram/math rendering in PDF exports (KaTeX/Mermaid ΓåÆ vector graphics).
- Multi-instance horizontal scaling, Redis, object storage migration (designs leave seams; not built).
- Prompt-injection hardening beyond current scoping (low blast-radius, revisit with billing).
