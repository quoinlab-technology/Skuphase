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

### Planned

- Platform membership and internal operations console.
- In-app feedback, support tickets, and notification inbox.
- Cross-school usage, health, and AI-cost reporting.

## [2.0.0] - 2026-10-10

- Pilot-ready SkuPhase release with school administration, teacher workflows,
  curriculum tooling, AI/manual exam generation, document exports, Supabase
  storage branding, and production deployment support.
