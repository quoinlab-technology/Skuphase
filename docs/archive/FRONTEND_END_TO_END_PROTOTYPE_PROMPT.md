# SkuPhase Frontend Prototype Prompt (V0 / AI Studio)

Use this exact prompt in V0 or AI Studio:

---
Design and generate a complete multi-page web app prototype for **SkuPhase**, an AI-assisted exam workflow platform for Nigerian schools.  
This is a **high-fidelity UI/UX prototype**, not production code.  
Use realistic fake data and fully connected flows between pages.

## Visual Direction
- Theme style: clean, institutional, modern, calm, trustworthy.
- Color palette (strict):
  - Primary deep green: `#00412E`
  - Secondary sage: `#96BF8A`
  - Light neutral background: `#E8EAE5`
  - White surfaces: `#FFFFFF`
- Avoid dark mode.
- Use soft shadows, large rounded cards, subtle layering.
- Keep contrast high for accessibility.
- Typography: professional and legible (e.g., Manrope, Sora, or Nunito Sans).
- Motion: light transitions only (card hover, panel reveal, modal open).

## Product Positioning
SkuPhase is **not** a full school management system.  
It focuses on:
1. Curriculum/lesson note document ingestion
2. Asset extraction and management (images/diagrams/formula references)
3. Controlled exam generation workflow (admin-governed AI calls)
4. Teacher/auditor review and refinement
5. Preflight quality checks and export

## Roles and Access
Create role-aware UI for:
1. `school_admin`
2. `teacher`
3. `auditor`

Show nav visibility and action permissions by role.

## Required Global Layout
Create:
1. Public marketing shell (before login)
2. Auth shell (register/login)
3. App shell (after login) with:
   - left sidebar nav
   - top bar (school switch display, notifications, profile menu)
   - breadcrumb area
   - content canvas

Include:
1. Empty states
2. Loading/skeleton states
3. Error states
4. Success toasts
5. Confirm dialogs for destructive actions

## Public Pages (Landing)
Create these pages:
1. Landing page
   - Hero: “Generate Better Exams, Faster”
   - CTA: Start Free, Book Demo
   - Feature blocks: Document RAG, Asset References, Quality Preflight, Admin Approval
   - Pricing teaser cards
   - FAQ and footer
2. About / How it works
3. Contact page
4. Privacy and Terms placeholders

## Auth Pages
Create:
1. School + admin registration page (`/api/v1/auth/register`)
   - school fields + admin user fields in one form
2. Login page (`/api/v1/auth/login`)
3. Basic forgot-password placeholder UI (visual only)

## App Navigation Structure
Sidebar sections:
1. Dashboard
2. Exams
3. Generation Proposals
4. Question Bank
5. Documents
6. Assets
7. RAG Search
8. Users (admin only)
9. School Settings
10. Operations (admin only)

## Dashboard (Role-aware)
### Admin dashboard
Cards:
1. Exams generating
2. Under review
3. Approved
4. Failed last 24h
5. Documents pending/in-progress
6. Documents failed

Widgets:
1. Recent exams table
2. Pending proposals list
3. Assets awaiting review list
4. Quick actions (Generate Exam, Upload Document, Review Assets)

### Teacher dashboard
Cards:
1. My draft/manual exams
2. Exams awaiting my final submit
3. My proposals
4. My recent audit comments

### Auditor dashboard
Cards:
1. Open exams for review
2. Submitted comments
3. Pending proposal reviews

## Documents Module
Implement screens for:
1. Document list (`GET /api/v1/documents`)
   - filters by type, status, date
   - columns: name, type, size, pages, processing status, updated
2. Upload modal/page (`POST /api/v1/documents/upload`)
3. Document detail (`GET /api/v1/documents/{id}`)
4. Start processing action (`POST /api/v1/documents/{id}/process`)
5. Delete document confirmation (`DELETE /api/v1/documents/{id}`)
6. Visual assets tab (`GET /api/v1/documents/{id}/visual-assets`)

Include processing timeline states:
`pending -> in_progress -> completed/failed`

## Assets Module
Implement:
1. Asset list (`GET /api/v1/assets`)
   - filters: subject, grade, topic, asset_type, active/inactive
2. Upload asset modal (`POST /api/v1/assets/upload`)
3. Edit metadata drawer (`PATCH /api/v1/assets/{id}`)
4. Single review modal (`PATCH /api/v1/assets/{id}/review`) admin only
5. Batch review modal (`POST /api/v1/assets/review-batch`) admin only
6. Archive confirmation (`DELETE /api/v1/assets/{id}`)

Asset card/table must show:
1. thumbnail
2. reference code
3. type/source
4. description/ocr preview
5. status badge (`needs_review`, `approved`, `rejected`)
6. AI-usable badge

## RAG Search Module
Screen for semantic search:
1. Search form (`POST /api/v1/rag/search`)
2. Result cards: chunk text, similarity score, source doc, metadata
3. Quick open source document action
4. Empty result state

## Exams Module (Core)
Implement complete exam workflow:

### A. Generate exam (admin only)
Endpoint: `POST /api/v1/exams/generate`
Create multi-step wizard:
1. Subject + grade
2. Select source documents
3. Select approved assets (optional)
4. Configure sections:
   - section title
   - question type
   - num questions
   - marks
   - instruction type
   - answer count / compulsory logic
   - sub-part style
5. Custom instructions
6. Confirm and submit

### B. Manual exam submit (teacher/admin)
Endpoint: `POST /api/v1/exams/manual-submit`
Create exam composer:
1. Add/edit/reorder questions
2. MCQ/short/essay variants
3. Attach assets by `asset_ids`
4. Inline preview panel

### C. Exams list
Endpoint: `GET /api/v1/exams`
Columns:
1. subject
2. grade
3. status
4. workflow state
5. marks
6. created date
7. actions menu

### D. Exam detail page
Endpoint: `GET /api/v1/exams/{id}`
Sections:
1. metadata header
2. question list (with linked asset chips and inline figure previews)
3. quality summary panel
4. activity timeline

Actions:
1. Run preflight (`GET /api/v1/exams/{id}/preflight`)
2. Submit final (`POST /api/v1/exams/{id}/submit-final`) teacher/admin
3. Refine (`POST /api/v1/exams/{id}/refine`) admin
4. Refine from comments (`POST /api/v1/exams/{id}/refine-from-comments`) admin
5. Approve (`POST /api/v1/exams/{id}/approve`) admin
6. Export (`POST /api/v1/exams/{id}/export`) admin
7. Delete (`DELETE /api/v1/exams/{id}`) admin

### E. Preflight results modal/panel
Show:
1. pass/fail summary
2. issues table (blocking)
3. warnings table (non-blocking)
4. issue codes examples:
   - unresolved_asset_reference
   - broken_asset_link
   - inactive_asset
   - rejected_asset
   - formula_unbalanced_inline_dollar
   - formula_unbalanced_block_dollar
   - formula_unbalanced_round_delimiter
   - formula_unbalanced_square_delimiter
   - formula_unbalanced_environment

### F. Quality report screens
Endpoints:
1. `GET /api/v1/exams/{id}/quality-report`
2. `GET /api/v1/exams/{id}/quality-snapshots`

Show:
1. score trend
2. quality status
3. coverage metrics
4. warnings/errors

### G. Audit comments
Endpoints:
1. `POST /api/v1/exams/{id}/audit-comments`
2. `GET /api/v1/exams/{id}/audit-comments`

UI:
1. per-question comment thread
2. add suggested text/marking scheme
3. open/resolved state chips

## Generation Proposals Module
Teacher/auditor/admin can submit:
1. Create proposal (`POST /api/v1/exams/generation-proposals`)
2. List proposals (`GET /api/v1/exams/generation-proposals`)
3. Admin generates from proposal (`POST /api/v1/exams/generation-proposals/{id}/generate`)

Create:
1. proposal list with status filters
2. proposal detail drawer
3. generate-from-proposal modal (admin)

## Question Bank Module
Implement:
1. Save questions from exam (`POST /api/v1/exams/{id}/question-bank/save`)
2. Browse bank (`GET /api/v1/exams/question-bank/items`)
3. Edit bank item (`PATCH /api/v1/exams/question-bank/items/{item_id}`)

UI:
1. searchable bank grid/table
2. side-by-side item editor
3. “use in manual exam” action

## Users Module (Admin)
Implement:
1. Invite user (`POST /api/v1/users/invite`)
2. List users (`GET /api/v1/users`)
3. Update role (`PUT /api/v1/users/{user_id}/role`)
4. Remove user (`DELETE /api/v1/users/{user_id}`)

Include role badges and safety confirmation modals.

## School Settings Module
Implement:
1. School profile (`GET/PUT /api/v1/schools/{school_id}`)
2. School settings (`GET/PUT /api/v1/schools/{school_id}/settings`)

Tabs:
1. School profile
2. Branding
3. Exam defaults
4. LLM provider preferences (readable but guarded)

## Operations Module (Admin)
Implement:
1. Health view (`GET /api/v1/ops/health`)
2. Stats view (`GET /api/v1/ops/stats`)

Create compact ops dashboard:
1. queue counters
2. failures
3. timestamped health check

## UX Requirements
1. Use role-based disabled states with explanations.
2. For any blocked action, show clear reason and next step.
3. Provide inline helper text for Nigerian school context and exam structure.
4. Keep forms segmented and non-overwhelming.
5. Always include preview before final destructive/irreversible steps.

## Mobile + Desktop
1. Desktop: full sidebar and 2-column management layouts.
2. Tablet/mobile: collapsible sidebar, stacked cards, sticky primary action button.
3. Ensure every table has responsive card fallback.

## Output Expectations
Generate a complete clickable prototype with:
1. all pages listed above
2. all key modals/drawers
3. realistic fake records and statuses
4. linked navigation and action flows
5. consistent design tokens using the exact color palette

Do not generate backend code.  
Focus on a polished, implementation-ready front-end prototype blueprint.
---

