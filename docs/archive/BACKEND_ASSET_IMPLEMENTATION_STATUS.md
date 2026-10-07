# Backend Asset Implementation Status

Date: 2026-03-04
Scope: Backend-only foundation for lesson-note visuals, formula assets, and exam question references.

## What Is Implemented Now

1. New SQLAlchemy models:
- `LearningAsset` (`app/models/asset.py`)
- `DocumentVisualRef` (`app/models/asset.py`)
- `QuestionAssetRef` (`app/models/asset.py`)

2. Existing models wired to new relationships:
- `School.learning_assets`
- `User.learning_assets`
- `SchoolDocument.learning_assets`
- `SchoolDocument.visual_refs`
- `DocumentChunk.visual_refs`
- `Question.asset_refs`

3. Models package export updated:
- `app/models/__init__.py` now exports asset models.

4. New migration added:
- `app/migrations/versions/0008_learning_assets_refs.py`
- Creates tables:
  - `learning_assets`
  - `document_visual_refs`
  - `question_asset_refs`
- Adds indexes and uniqueness constraints for school-safe reference codes and question-asset mapping.

5. Exam schema updated for asset-aware flows:
- `ExamGenerationRequest.asset_ids`
- `QuestionResponse.asset_refs`
- `ManualQuestionInput.asset_ids`

6. Asset management APIs implemented:
- `POST /api/v1/assets/upload`
- `GET /api/v1/assets`
- `PATCH /api/v1/assets/{asset_id}`
- `PATCH /api/v1/assets/{asset_id}/review`
- `DELETE /api/v1/assets/{asset_id}`

7. Exam APIs now enforce and persist asset references:
- Generation request validates optional `asset_ids` are approved/AI-usable.
- Manual exam submit validates question-level `asset_ids` and stores `question_asset_refs`.
- Exam detail/update/manual responses now include `asset_refs` per question.

8. Exam generator prompt + storage updated:
- Pulls approved asset metadata into prompt context.
- Supports optional LLM output field `asset_ref`.
- Stores `asset_ref` mappings in `question_asset_refs`.

9. Preflight gate implemented:
- `GET /api/v1/exams/{exam_id}/preflight`
- Checks broken/unresolved/inactive/rejected asset links.
- `submit-final` and `approve` now block if preflight has issues.
- Formula markup delimiter checks are included (`$`, `$$`, `\(\)`, `\[\]`, `\begin...\end`).
- `export` now also blocks when preflight has issues.

10. Export rendering upgraded:
- Export now loads linked question assets and renders image blocks in PDF output.
- Missing/unreadable files degrade gracefully with placeholder text.

11. Generation output contract hardened:
- `asset_ref` is now strictly validated during parse before persistence.
- Rejects invented/unselected references.
- Rejects malformed or empty `asset_ref`.
- Rejects inline `asset_ref` markers in question text when JSON `asset_ref` field is missing.

10. Document processing now auto-extracts visuals:
- PDF pipeline optionally extracts embedded images when `fitz` is available.
- Auto-creates `learning_assets` (`asset_source=lesson_note`, `processing_status=needs_review`).
- Auto-links extracted visuals to source document through `document_visual_refs`.
- OCR text is attempted when OCR dependencies exist; otherwise extraction still succeeds without OCR.

11. Document visual review endpoint added:
- `GET /api/v1/documents/{document_id}/visual-assets`
- Returns extracted/linked assets for that document so staff can review and approve.

12. Batch asset review endpoint added:
- `POST /api/v1/assets/review-batch`
- Admin can approve/reject many assets by `asset_ids` or `source_document_id` in one request.

13. Deployment toggles added:
- `PDF_IMAGE_EXTRACTION_ENABLED` (default `true`)
- `OCR_ENABLED` (already present)

14. Background reliability hardening (no external broker):
- Retry/backoff added to FastAPI background handlers for document processing and exam generation.
- Configurable through env:
  - `BACKGROUND_RETRY_ATTEMPTS`
  - `BACKGROUND_RETRY_BASE_DELAY_SECONDS`
- Idempotency improvements:
  - document reprocessing clears existing chunks before insert,
  - exam regeneration clears previous `exam_context` rows before insert.

15. Primary-exam rendering guidance in generation:
- Prompt now includes primary puzzle/layout instructions for markdown-friendly output.
- Encourages renderer-safe structures (tables/lists/compact diagram blocks) and asset_ref usage for pictures.
- Parser now rejects unbalanced markdown fenced code blocks in question text.

## Why This Matters

This creates the backend contract for a dual-channel RAG system:
- text channel (existing `document_chunks` + pgvector),
- visual/formula channel (new `learning_assets` + refs).

It supports your cost policy:
- admin-only LLM calls,
- metadata-only asset injection to LLM,
- no mandatory multimodal API dependency.

## Remaining Backend Work (Next Implementation Steps)

1. Asset API endpoints
- Upload/list/update/archive assets
- Approve/reject `is_ai_usable`
- Filter by subject/grade/topic/source

2. Document processing extension
- Extract embedded images from PDFs
- OCR image text where useful
- Auto-create draft `learning_assets` + `document_visual_refs`
- Mark as `needs_review`

3. Exam generation integration
- Validate request `asset_ids` belong to school and are `is_ai_usable=true`
- Inject selected asset metadata into prompt
- Parse model output `asset_ref` and map to `question_asset_refs`
- Reject unknown/non-selected references

4. Manual exam integration
- Persist `ManualQuestionInput.asset_ids` into `question_asset_refs`

5. Quality/preflight checks
- Add unresolved asset check before `submit-final` and `approve`
- Add formula syntax quality checks
- Add asset coverage metrics to quality snapshots

## Faststrap Native Capability Contract (No Frontend Build Yet)

Faststrap should natively support:
1. Markdown + LaTeX rendering
2. Asset picker and preview
3. Unresolved-asset warnings in draft preview
4. Formula parse/lint hints before submission
5. Print preview checks for image/table overflow

## Suggested Execution Order

1. Run migration `0008_learning_assets_refs`.
2. Implement asset CRUD endpoints.
3. Integrate manual question `asset_ids` persistence.
4. Integrate generation `asset_ids` prompt + output mapping.
5. Add preflight validation gates.
