# SkuPhase Asset + Formula Rendering Plan (Nigeria Exam Realism)

Date: 2026-03-04
Context: This plan factors in teacher-owned exam requirements, admin-only LLM calls, low-token policy, and Faststrap-based frontend delivery.

## 1. Goal

Deliver native-feeling Nigerian exam papers for STEM and reasoning subjects with:
- formulas rendered correctly,
- diagram/image questions handled reliably,
- minimal complexity and low operating cost for underserved private schools.

## 2. Guiding Constraints

1. Admin-only LLM triggers remain enforced.
2. Typical exam should use 2 LLM calls, max 3.
3. No mandatory multimodal AI dependency in v1.
4. Backend validates quality and workflow; frontend handles rich rendering UX.

## 3. Decision Summary

1. Use asset references, not direct image-to-LLM in v1.
2. Feed LLM asset metadata (label + description + subject tags), not raw images.
3. LLM outputs question content with `asset_ref` tokens.
4. Frontend resolves `asset_ref` to actual uploaded files.
5. Final submit/approval gates block unresolved assets or broken math markup.

## 4. Architecture Split (Backend vs Frontend)

## Backend Responsibilities

1. Asset storage metadata API
- upload record (file URL/path, label, description, subject, class, tags, owner)
- list/search/filter assets
- deactivate/archive assets

2. Question-asset linkage
- allow question fields: `asset_id`, `asset_ref`, `asset_caption`, `asset_required`
- enforce school tenancy and subject/class constraints

3. Generation input contract
- accept selected `asset_ids` in exam request package
- inject selected asset metadata into LLM prompt
- require generated output references existing asset refs only

4. Validation gates
- reject final submission if `asset_required` question has no resolved asset
- validate math syntax markers (basic LaTeX sanity checks)
- export preflight validation endpoint

5. Persistence and auditability
- keep asset usage log per exam/question
- keep quality snapshots (already implemented) including asset coverage signals

## Frontend (Faststrap) Responsibilities

1. Rich rendering
- Markdown renderer for question text
- math renderer (KaTeX/MathJax) for formulas
- table rendering and figure captions

2. Teacher authoring UX
- asset upload panel with preview + tags
- drag/select asset into question requirement builder
- render question previews exactly as export-like layout

3. Workflow ergonomics
- unresolved asset indicator chips
- formula render error highlighting
- print-readiness checks visible before submit-final

4. Optional frontend-native helpers
- simple equation helper snippets
- diagram placeholder helper blocks (`[FIGURE:ASSET_X]`)
- client-side markdown lint hints before send

## 5. Scope Phases

## Phase A (Immediate, 1-2 weeks): Asset-Referenced Questions v1

Backend:
1. Add `exam_assets` table (or `question_assets`) and endpoints.
2. Add question-level asset reference fields.
3. Add final-submit validation for unresolved assets.
4. Add export preflight endpoint (`/exams/{id}/preflight`).

Frontend:
1. Asset upload/list/filter in teacher portal.
2. Attach selected assets in requirement package.
3. Question preview with image embedding.

Acceptance:
- Teacher can upload image, attach to requirement, and admin-generated question can reference it.
- Approval blocked when unresolved figure references exist.

## Phase B (Next, 1 week): Formula Rendering and Validation

Backend:
1. Add formula syntax checker (basic delimiters and parseability hints).
2. Store formula validation issues in quality report.

Frontend:
1. Render LaTeX with KaTeX/MathJax.
2. Show inline formula parse errors before submission.

Acceptance:
- Math-heavy questions render consistently in teacher preview and final export.

## Phase C (Later): Diagram Helpers and Templates

1. SVG template snippets for basic circuits/graphs/tables.
2. Per-subject template packs (Physics/Maths/Quantitative/Verbal).
3. Optional AI-assisted merge of bank questions (deferred).

## 6. Prompt Updates Required

1. Add asset section in prompt:
- `ASSET_REF`, label, short description, allowed usage note.
2. Force output contract:
- if question depends on figure, include `asset_ref`.
3. Keep single-call internal protocol:
- PLAN -> DRAFT -> CRITIQUE -> REPAIR -> FINAL CHECK.

## 7. Risks and Mitigations

1. Risk: Teachers upload low-quality images.
- Mitigation: frontend image quality checks + minimum resolution warning.

2. Risk: LLM invents non-existent assets.
- Mitigation: backend validator rejects unknown `asset_ref`.

3. Risk: Export mismatch from preview.
- Mitigation: common markdown/math rendering profile and preflight checks.

4. Risk: Workflow friction in low digital maturity schools.
- Mitigation: very simple upload/tag/attach flow, with defaults and templates.

## 8. What Frontend Can Natively Handle (to reduce backend complexity)

1. Markdown rendering and sanitization display.
2. LaTeX rendering and user-visible parse feedback.
3. Visual editor conveniences (toolbar, formula snippets, figure insert controls).
4. Realtime preview and print-preview layout checks.
5. Local image optimization before upload (resize/compression hints).

## 9. Out of Scope for This Phase

1. Full multimodal image-understanding LLM pipeline.
2. Automatic image generation from text.
3. AI merge/remix of multiple question-bank items (explicitly deferred).

## 10. Execution Order for Next Sessions

1. Implement Asset-Referenced Questions v1 backend schema + APIs.
2. Implement frontend asset attach + preview flow in Faststrap.
3. Add formula validation + renderer integration.
4. Add export preflight gate and rollout checklist updates.
