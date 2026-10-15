# Changelog

All notable changes to SkuPhase are recorded here. Entries describe user-visible
features, operational changes, security fixes, and important migrations.

## [Unreleased]

### Added

- Routed student exam printing through the browser's KaTeX-enabled two-column
  print view instead of the ReportLab export that flattened matrix notation.
  Direct PDF export is now limited to teacher marking guides and OMR sheets;
  stale student-paper export requests are redirected to the formatted print view.

- Fixed the notification badge to count durable unread notifications instead of
  exams awaiting review; the badge now stays hidden when the inbox is empty.
- Removed the document-header frame from exam PDFs, rendered inline matrix
  expressions in compact row notation instead of stripped LaTeX, and added a safe
  NGN fallback for PDF environments without a reliable Naira glyph.
- Fixed the AI exam wizard's initial Step 1 → Step 2 transition, made class
  selection refresh its dependent subject list without a duplicate curriculum
  request, and placed Grade / Class before Subject.
- Added configurable document branding: school administrators can set a print
  display name for the school, while personal-workspace owners can opt in to a
  custom document name and Supabase-hosted logo. Personal documents use the
  registered account name and no custom logo until branding is enabled; this
  setting never renames the account.
- Added a workspace-wide curriculum source setting: school administrators select
  the school's source and individual teachers select theirs from Personal
  Settings. Curriculum browsing, guided teaching, and new exam workflows use
  that source; AI and manual exam records retain source provenance. The setting
  rejects sources absent from the curriculum catalogue.
- Connected teaching scope changes to an in-place loading indicator and refreshed
  class-specific subjects, weeks, and lesson-plan defaults; clarified the shared
  syllabus tracker and return teachers to its expanded records after updates.
- Rebalanced the Teaching workspace tools and coverage panel for wide screens,
  removed the extra wrapper around lesson-plan cards, added a safe formatted
  lesson-note preview, and compacted refinement/export actions on phones.
- Branded lesson-note PDF and Word exports with the school's uploaded logo,
  school-name PDF watermark, and title-based filenames; PDF math now renders
  common TeX and plain-text sub/superscripts typographically instead of flattening
  formula source to ordinary text.
- Split weekly worksheet authoring and recent worksheets into a focused Teaching
  workspace page; the main teaching page now emphasizes lesson planning and
  school coverage. Worksheet authoring starts with one question, adds rows on
  demand, and keeps the final question protected from accidental removal.
- Improved Teaching page plan-card spacing and responsive widths, made school
  coverage details collapsible, and branded the worksheet question removal
  action. Worksheet PDFs now render inline and display TeX formulas as the same
  safe vector math used by exam PDF exports.
- Hardened the AI exam wizard's curriculum-week validation: an empty selection
  stays on Step 2 with clear feedback and restores the Next button; valid
  selection continues normally. Replaced inline HTMX handlers in the wizard
  and Question Bank delete modal with CSP-safe event listeners.
- Made exam detail and print views tolerate legacy records without a term,
  added specific document titles, and verified the bundled logo fallback.
- Improved lesson-note PDF/DOCX formatting by rendering inline Markdown emphasis,
  omitting horizontal-rule source markers, and presenting inline TeX in a
  readable safe-text form in PDFs. Reflowed OMR candidate fields and scoring
  area for small screens without changing its print sheet layout.
- Fixed recurring post-login expiry loops caused by stale, oversized cookie
  sessions: sign-in now starts from a clean session, expiry/sign-out clear all
  cookie-backed state, curriculum catalogue data stays out of the cookie, and
  queued-generation context is compact and bounded.
- Correctly place public, authentication, and workspace page titles in the HTML
  document head, with branded defaults for untitled pages. Login now redirects
  an already-authenticated user to the workspace and displays the one-time
  signed-out message after logout.
- Fixed Teaching workspace outline-button variants so Faststrap's default
  primary style no longer overrides the brand-outline appearance.
- Added a Faststrap confirmation modal before removing a question from the
  manual exam composer; cancellation keeps the question, and the exam retains
  its minimum-one-question safeguard.
- Restored lesson-note refinement buttons immediately when an unsaved-edit
  confirmation cancels submission, preventing a stale spinner/disabled state.
- Fixed exam-list search failing because the API did not declare its search
  query parameter; the desktop exam table is now a labeled, keyboard-scrollable
  region, and mobile long titles no longer push the card menu out of view.
- Teaching workflow safeguards: unsaved lesson-note refinement confirmation,
  full expandable curriculum-week topics, accessible scope guidance, and
  structured worksheet question authoring with marks, type, options, and
  staff-only answer keys. Multiple-choice options print on learner PDFs while
  answer keys remain available only in the staff marking guide; worksheet
  content and exports are restricted to staff roles.
- Clarified school-wide syllabus coverage metrics and their teacher/admin
  responsibilities; invalid subject resets after a class change are now
  explained in the workspace.
- Company operations-layer implementation plan covering platform access,
  monitoring, support, notifications, auditability, and phased delivery.
- Initial explicit platform-membership model and role dependency foundation.
- Private platform operations shell with protected overview and school-directory
  routes, including cross-school health, queue, usage, and activity summaries.
- Added a trusted operator script for granting or revoking platform memberships
  without exposing credentials in the application UI.
- Added durable school feedback tickets, a user notification inbox, read-state
  actions, and a platform support queue.
- Added the private platform support-case workflow: linked ticket detail pages,
  status and resolution updates, internal notes, support replies, and requester
  notifications. Added the `feedback_messages` persistence migration and
  Faststrap-based operator forms.
- Added active platform-member assignment for support cases, including
  assign/unassign controls and a notification to the newly assigned operator.
- Added a private platform notification inbox with unread state, mark-read, and
  mark-all-read actions, linked from the platform shell notification bell.
- Added the Phase 0 audit-event foundation: append-only sanitized event storage,
  request correlation IDs, platform audit API, and a read-only Faststrap audit
  viewer for permitted platform roles.
- Added bounded audit investigation filters for action and success result in the
  platform API and Faststrap audit page.
- Added audit coverage for school feedback submission and documented the Phase
  0 platform access, retention, and redaction contract.
- Added the first Phase 1 operations views: bounded cross-school user directory,
  searchable user table, linked school operational profiles, and school health
  summaries for staff, exams, jobs, support, and AI usage.
- Completed the Phase 1 pilot operations MVP with generation-job monitoring,
  dependency health checks, daily bounded usage reporting, and guarded failed-job
  retry controls.
- Started Phase 2 with a dedicated `/internal/login` entry point for company
  operators. It reuses secure session authentication, then checks platform
  membership before allowing access to the private operations console.
- Added school-facing feedback report detail pages with public support replies,
  status context, and direct links from the report history and notifications.
  Internal support notes remain hidden from school users.
- Added durable notification email delivery tracking: important support events
  are queued after the in-app notification commit, retried with bounded
  backoff, and surfaced as pending or failed counts in platform health views.
- Added a private platform email-delivery monitor with recipient/status/error
  visibility and a guarded retry action for terminal notification failures.
- Completed the Phase 2 pilot operations scope: private operator access,
  school feedback conversations, durable notifications, preferences, queued
  email retries, and delivery recovery visibility.
- Completed Phase 3 pilot product intelligence: aggregate provider/action cost,
  manual-versus-AI adoption, generation latency, subject failure trends,
  quality snapshots, and school onboarding health with bounded filters at
  `/internal/platform/insights`.
- Completed Phase 4 pilot governance: incident lifecycle tracking, audited
  time-limited support-access grants, curriculum version validation/publish/
  rollback records, sanitized audit CSV export, retention reporting, and
  owner-only audit purge controls.

### Planned

- Platform membership and internal operations console.
- In-app feedback, support tickets, and notification inbox.
- Cross-school usage, health, and AI-cost reporting.

## [2.0.0] - 2026-10-10

- Pilot-ready SkuPhase release with school administration, teacher workflows,
  curriculum tooling, AI/manual exam generation, document exports, Supabase
  storage branding, and production deployment support.
