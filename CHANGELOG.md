# Changelog

All notable changes to SkuPhase are recorded here. Entries describe user-visible
features, operational changes, security fixes, and important migrations.

## [Unreleased]

### Added

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

### Planned

- Platform membership and internal operations console.
- In-app feedback, support tickets, and notification inbox.
- Cross-school usage, health, and AI-cost reporting.

## [2.0.0] - 2026-10-10

- Pilot-ready SkuPhase release with school administration, teacher workflows,
  curriculum tooling, AI/manual exam generation, document exports, Supabase
  storage branding, and production deployment support.
