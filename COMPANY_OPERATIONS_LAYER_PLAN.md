# SkuPhase Company Operations Layer

## Purpose

SkuPhase currently serves two audiences:

1. **School users** — school administrators, teachers, auditors, and future school staff roles who create and manage educational work inside one school workspace.
2. **SkuPhase company staff** — the people responsible for keeping the platform reliable, supporting pilot schools, monitoring AI and document-generation quality, managing curriculum operations, and learning how the product is used.

The company operations layer is the internal control plane for the second audience. It is not a larger version of the school-admin dashboard and it must not become another approval queue for teachers.

The school-admin area governs one school. The company operations area monitors and supports the whole SkuPhase service.

The first release should optimize for pilot reliability and learning, not premature billing complexity.

---

## Product strategy

The company dashboard exists to answer five operational questions quickly:

1. **Is SkuPhase healthy right now?**
2. **Which schools and users are active, blocked, or at risk?**
3. **Where are generation, curriculum, export, email, or storage failures occurring?**
4. **What are schools asking for, and how quickly are we responding?**
5. **Which features create real educational value and sustainable operating cost?**

The operating layer should therefore provide:

- cross-school visibility without breaking tenant isolation;
- actionable alerts instead of raw log flooding;
- aggregate analytics before content surveillance;
- an in-app feedback and support loop;
- an immutable audit trail for sensitive company actions;
- AI usage and cost controls;
- reliable notifications through Faststrap components;
- enough curriculum and document observability to diagnose source-data problems;
- a clear path from pilot operations to future commercial administration.

### What this layer is not

It is not intended initially to provide:

- a full CRM;
- payment collection or invoice accounting;
- marketing automation;
- unrestricted access to every school's private exam content;
- a replacement for school administration;
- a second teacher approval workflow;
- a generic BI warehouse before product metrics are understood.

---

## Current SkuPhase foundation and gaps

### Existing foundations

The current application already contains useful building blocks:

- school and user tenancy in `app/models/school.py` and `app/models/user.py`;
- school-scoped operational endpoints in `app/api/v1/ops_router.py`;
- AI and action usage records in `app/models/usage_log.py`;
- durable generation jobs and retry state in `app/models/job.py`;
- login-attempt records in `app/models/login_attempt.py`;
- exams, lesson plans, curriculum, question-bank, plans, and subscriptions;
- structured request logging and request IDs;
- Faststrap cards, tables, modals, toasts, loading buttons, badges, and spinners;
- school-facing flash/toast feedback in `app/frontend/components/feedback.py`;
- role-based school-admin and teacher boundaries.

### Missing capabilities

The following gaps must be closed before the company dashboard can be considered production-capable:

1. There is no explicit platform/company role model.
2. Existing operations statistics are school-admin scoped, not platform scoped.
3. There is no unified immutable application audit-event stream.
4. There is no feedback, complaint, or support-ticket model.
5. There is no notification inbox or notification delivery engine.
6. Usage logs are useful but not yet shaped for cross-school analytics and cost reporting.
7. Provider latency, provider errors, retries, and job age are not centrally aggregated.
8. There is no internal school/user directory.
9. There is no support-agent workflow or safe support-access mechanism.
10. Curriculum ingestion and document processing lack an internal operations view.
11. There is no alert acknowledgement/resolution workflow.
12. Retention, redaction, and platform-admin data-access rules are not documented as one policy.

These gaps should be implemented deliberately rather than solved with broad access to existing school-admin endpoints.

---

## Access and security model

### Separate platform roles

The first platform roles should be:

- `platform_owner` — unrestricted company operations and security control;
- `platform_admin` — schools, users, support, operations, and configuration;
- `support_agent` — schools, users, feedback, and limited support actions;
- `analyst` — read-only aggregate analytics and reports;
- `content_operator` — curriculum and shared-library operations only.

These are not school roles. A platform staff member should not be forced into a school tenant to gain access to company tooling.

During the pilot foundation, access is granted to an existing verified user with
the trusted operator command `scripts/grant_platform_membership.py`. This keeps
the first bootstrap path out of the public UI. A later platform-owner UI can
delegate memberships with the same permission and audit rules.

### Recommended data model direction

For the first implementation, a platform role may be introduced with an explicit migration and a nullable school relationship. The safer long-term model is:

- `users` remains the identity table;
- `platform_memberships` grants a user a company role and permission set;
- a platform member may also have a normal school account, but the two contexts are explicit;
- platform membership is never inferred from email domain or school ownership;
- all platform actions are recorded with actor, permission, target, and reason.

Do not expose platform access by adding `platform_admin` to every school-admin authorization check. Platform endpoints should have their own dependency and permission checks.

### Tenant and privacy rules

- School users can access only their own school's data.
- Company staff can access only the aggregate data required for their role.
- Raw question/exam content is not shown by default in company analytics.
- Support access to a school's content is explicit, time-limited, read-only by default, and audited.
- Sensitive fields are redacted from logs and notification bodies.
- Secrets, tokens, passwords, prompts containing private data, and API credentials are never persisted in audit events.
- Every platform mutation must carry a request/correlation ID.

---

## Operating-layer modules

### 1. Operations overview

The company home page should show:

- active schools;
- active users today and this week;
- exams generated today, this week, and this month;
- generation success rate;
- failed and stuck jobs;
- AI tokens and estimated cost;
- pending critical support cases;
- database, worker, email, storage, and provider health;
- alerts requiring acknowledgement.

Charts should include:

- daily generation volume;
- weekly active schools;
- monthly active users;
- success/failure trend;
- generation latency;
- provider error rate;
- token and estimated-cost trend;
- exports and document-processing volume.

All chart data should come from aggregated API queries with date-range and school filters. The browser must not receive an unbounded raw log dataset.

### 2. Schools and tenants

The school directory should support search, filters, pagination, and sorting by:

- name;
- active/inactive state;
- onboarding date;
- last activity;
- staff count;
- generation volume;
- failed jobs;
- open support cases;
- pilot cohort;
- plan/subscription state when commercial administration begins.

School detail should show a compact operational profile:

- contact and status;
- staff and verification summary;
- recent activity;
- generation success/failure;
- usage and estimated cost;
- storage and document activity;
- open feedback;
- curriculum/import health.

Initial actions should be safe and reversible:

- view school;
- add internal note;
- contact administrator;
- suspend/reactivate with confirmation and reason;
- export an operational report.

Deletion, bulk suspension, and unrestricted impersonation are deferred until governance is mature.

### 3. Users and access

The company user directory should show:

- user name and email;
- school;
- role;
- verification state;
- active/suspended state;
- last login;
- recent failed login count;
- recent activity;
- open support cases.

Safe support actions:

- resend verification email;
- revoke sessions;
- trigger password-reset email;
- suspend/reactivate with reason;
- correct school assignment through a guarded workflow.

Every action must show a confirmation modal, use a loading state, and create an audit event.

### 4. Usage, AI economics, and quotas

Usage analytics must be available by day, week, month, school, user, provider, action, and exam/job where appropriate.

Track:

- exam generation;
- refinement;
- lesson-note generation;
- worksheet generation;
- document processing and embeddings;
- exports;
- diagram/asset processing;
- tokens used;
- estimated provider cost;
- request duration;
- retries;
- success/failure reason.

The current `UsageLog` should be extended carefully with indexes and normalized fields where reporting requires them. Free-form metadata may remain for provider-specific details, but core reporting dimensions should not depend on parsing text JSON.

The first version should expose usage and alerts, not hard billing enforcement. Per-school and per-user quotas can be added as mechanical safeguards without introducing pricing administration.

### 5. Generation jobs and provider health

Build a queue monitor around `GenerationJob`:

- pending count;
- running count;
- succeeded count;
- failed count;
- retry count;
- oldest job age;
- provider;
- duration;
- sanitized last error.

Actions:

- retry a failed job;
- cancel a stuck job;
- mark an incident investigated;
- open the related school or support case.

Provider metrics should include latency, timeout rate, parse failure rate, quota errors, and fallback-provider usage. Provider secrets and full prompts must never appear in the UI.

### 6. Feedback, complaints, and customer care

Add an in-app feedback entry point available from the authenticated shell. It should be short enough for a teacher on a mobile phone:

- category;
- short description;
- optional screenshot or attachment;
- current page/context automatically captured;
- optional related exam or document;
- submit button with Faststrap loading state.

The support record should contain:

- ticket ID;
- school and user;
- category and severity;
- description;
- attachments;
- route/context;
- browser/device metadata;
- status;
- assigned agent;
- internal notes;
- user-visible responses;
- timestamps and resolution reason.

Categories:

- bug;
- exam-generation quality;
- curriculum issue;
- PDF/export problem;
- account/access;
- feature request;
- billing/plan question;
- general complaint.

Statuses:

- new;
- acknowledged;
- investigating;
- waiting on school;
- resolved;
- closed.

Severity:

- critical — platform unavailable or data-loss risk;
- high — core workflow blocked;
- normal — degraded workflow;
- low — cosmetic issue or suggestion.

### 7. Faststrap notification engine

The notification engine should provide both an in-app inbox and optional email delivery. It should be a reusable platform service, not page-specific toast code.

#### Notification model

Create a notification record containing:

- recipient user;
- optional school;
- notification type;
- title;
- short body;
- severity/tone;
- target URL;
- related entity type and ID;
- read timestamp;
- archived timestamp;
- created timestamp;
- delivery state for email, if applicable.

Keep the body concise and avoid sensitive content. Store event references rather than copying large payloads.

#### Notification types

Initial types should include:

- exam generation completed;
- exam generation failed;
- document processing completed;
- document processing failed;
- staff invitation accepted;
- email verification reminder;
- support ticket updated;
- support ticket assigned;
- system incident;
- quota or unusual usage warning;
- curriculum import completed/failed.

#### Faststrap UI components

Use consistent Faststrap components:

- header bell with unread count;
- notification dropdown for recent items;
- full notification inbox page;
- unread/read state;
- mark-as-read and mark-all-read actions;
- severity badges;
- empty state;
- loading buttons/spinners;
- toast for immediate confirmation;
- modal for destructive or bulk actions.

Toasts communicate the immediate result. The inbox preserves the event so it is not lost when the user leaves the page.

#### Delivery and reliability

- In-app notifications are written transactionally with the source event where possible.
- Email notifications are queued and retried separately.
- Duplicate events use an idempotency key.
- Failed email delivery is visible to company operations.
- User preferences control non-critical notifications.
- Critical security and service incidents cannot be silently disabled.
- Notification endpoints are paginated and indexed by recipient/read state.

### 8. Audit and security centre

Add an append-only `audit_events` table. Each event should include:

- actor user;
- actor role/context;
- school scope, if applicable;
- action name;
- target type and ID;
- success/failure;
- timestamp;
- request/correlation ID;
- IP/device metadata where lawful and useful;
- sanitized JSON metadata.

Record at minimum:

- login success/failure;
- verification and password reset;
- invitation events;
- role and school changes;
- school setting changes;
- exam generation/refinement/export;
- document and logo changes;
- account suspension;
- platform-admin access;
- support access/impersonation;
- data exports;
- job retries and cancellations;
- curriculum changes/imports.

The audit viewer should support filters by actor, school, action, date range, target, and success state. It should be read-only for most roles and export access must itself be audited.

### 9. Quality and product intelligence

Measure whether the product is useful, not merely available:

- generation success rate;
- preflight failure rate;
- average quality score;
- teacher edit/regeneration rate;
- manual versus AI exam usage;
- lesson-note and worksheet usage;
- export frequency;
- repeated errors by subject/grade;
- curriculum gaps reported;
- schools that become inactive after onboarding;
- time from signup to first successful output.

Use aggregate views by default. Content inspection should require a legitimate support or quality reason and be audited.

### 10. Curriculum and document operations

Internal curriculum operations should expose:

- curriculum versions;
- import and OCR jobs;
- failed parsing jobs;
- missing subjects/grades;
- duplicate or suspicious entries;
- source-document provenance;
- recently corrected topics;
- coverage gaps;
- document-processing latency.

Curriculum changes require versioning, preview, validation, and rollback. A global curriculum edit can affect every school and must never be an untracked direct database change.

---

## Data and API design

Create platform-scoped APIs rather than widening school APIs.

Suggested endpoint families:

```text
/api/v1/platform/overview
/api/v1/platform/schools
/api/v1/platform/schools/{school_id}
/api/v1/platform/users
/api/v1/platform/jobs
/api/v1/platform/usage
/api/v1/platform/providers
/api/v1/platform/audit-events
/api/v1/platform/feedback
/api/v1/platform/notifications
/api/v1/platform/alerts
/api/v1/platform/curriculum-operations
```

Each endpoint must have:

- explicit platform permission dependency;
- pagination and bounded date ranges;
- tenant-safe filters;
- consistent error schema;
- request IDs;
- rate limits for expensive reports;
- tests for unauthorized school-admin and teacher access.

Avoid returning raw SQL-shaped data. Return stable dashboard schemas designed around the UI and reporting use case.

### Recommended core tables

The exact schema can be refined during Phase 0, but the operating layer will likely need:

- `platform_memberships`;
- `audit_events`;
- `notifications`;
- `notification_deliveries`;
- `feedback_tickets`;
- `feedback_messages`;
- `feedback_attachments`;
- `platform_alerts`;
- `support_access_sessions`;
- `usage_daily_rollups`;
- optional `provider_health_samples`.

Do not create daily rollups until the raw metrics and definitions are stable. Add them when query volume or dashboard latency requires it.

---

## Faststrap implementation standards

Every new operation-facing page or control should follow the existing SkuPhase visual language and Faststrap conventions:

- use Faststrap `Card`, `Table`, `Badge`, `Modal`, `Toast`, `EmptyState`, `Spinner`, and `LoadingButton` components;
- show a spinner on every network-backed action;
- disable duplicate submissions while a request is running;
- use Faststrap modal confirmation for destructive actions;
- use responsive cards/tables that remain usable on small mobile screens;
- provide empty, loading, error, and stale-data states;
- expose accessible labels and keyboard navigation;
- keep chart legends and labels readable at mobile widths;
- avoid browser `alert()` and unstyled native dialogs;
- capture screenshots at desktop and narrow mobile widths for every new page/component;
- keep company-only navigation hidden from school users.

The notification bell and support entry point should be part of the shared authenticated shell, not duplicated on individual pages.

---

## Phased implementation path

### Phase 0 — Operating-layer foundation and threat model

**Status: COMPLETE for pilot foundation (2026-10-11).** The platform
membership boundary, correlation-aware append-only audit stream, redaction
contract, bounded audit API/viewer, support-event hooks, and permission tests
are implemented. Additional low-risk event hooks (such as every export and
school-setting mutation) remain a tracked extension of the same service and do
not block Phase 1 delivery.

Deliver:

- platform-role decision and permission matrix;
- platform authentication/access boundary;
- audit-event taxonomy;
- privacy, retention, and redaction rules;
- request/correlation-ID standard;
- data dictionary for usage, job, quality, and support metrics;
- migration strategy and indexes;
- authorization and tenant-isolation tests.

Exit criteria:

- a school user cannot reach platform endpoints;
- a platform analyst cannot perform admin mutations;
- every planned dashboard metric has a defined source and time basis;
- sensitive data handling is documented.

### Phase 1 — Company operations MVP

**Status: COMPLETE for pilot operations (2026-10-11).** The private console now
has bounded school and user directories, school operational profiles, queue and
health monitoring, daily usage reporting, audit visibility, and a guarded retry
action for failed generation jobs. Rich provider telemetry, incident records,
and advanced charting remain Phase 3/4 enhancements.

Deliver:

- platform staff login and guarded navigation;
- operations overview;
- school directory and school detail;
- cross-school user directory;
- job queue monitor;
- database/worker/provider health summary;
- basic daily/weekly/monthly usage aggregates;
- read-only audit-event viewer.

Exit criteria:

- company staff can identify an unhealthy school, job, or provider without database access;
- dashboard queries are paginated and bounded;
- all platform actions and access attempts are audited;
- desktop and mobile visual verification is complete.

### Phase 2 — Feedback, support, and notifications

**Status: COMPLETE for pilot operations (2026-10-12).** The phase now has a
dedicated internal login boundary, school feedback and reply conversations,
durable in-app notifications, preferences, queued email delivery, retries,
failure visibility, and operator recovery controls. Secure support attachments
are intentionally deferred until the private-storage/signed-download contract
is implemented; public school branding storage must not be reused for private
support evidence.

Deliver:

- feedback button in the authenticated shell;
- feedback/ticket data model;
- school-user submission flow;
- company support queue;
- assignment, status, severity, notes, and replies;
- Faststrap notification records and inbox;
- unread bell/count;
- notification preferences;
- queued email notifications for important events;
- retry and failure visibility.

Secure support attachments are deferred to the governance/storage hardening
work so pilot feedback cannot accidentally expose private files through the
public school-assets bucket.

Exit criteria:

- a teacher can submit a problem from mobile in under one minute;
- the company team receives an in-app notification;
- the school user can see acknowledgement and replies;
- no notification is silently lost on navigation or refresh;
- email failure does not delete the in-app notification.

Implementation note: support notifications now remain durable in-app first;
important support events may also enter the database-backed email queue. The
worker retries provider failures without deleting the in-app record, and the
platform overview/health endpoints expose pending and terminally failed email
counts for operator follow-up.

Operators can now inspect individual queued deliveries and requeue a terminal
failure from the private console; each retry is recorded in the audit stream.

### Phase 3 — Usage, AI cost, and product intelligence

**Status: COMPLETE for pilot operations (2026-10-12).** The private console now
includes a bounded Product insights view at `/internal/platform/insights`, backed
by aggregate-only reporting. It covers provider/action spend, manual-versus-AI
adoption, subject-level generation failures, quality snapshot status, generation
queue latency, and active-school onboarding health. The view supports a 7–90 day
window and optional school/user identifiers, while excluding prompts, answers,
question text, and other private exam content.

Metric definitions are explicit: usage and estimated cost come from `UsageLog`
grouped by action/provider; AI adoption counts generation and refinement actions
while manual adoption counts `manual_exam_submission`; generation latency is the
elapsed time from queue creation to a succeeded or failed terminal job (with
average and p95); quality metrics are persisted `ExamQualitySnapshot` aggregates;
and a school is inactive for the selected window when it has no exam created
during that period. These definitions make reports reproducible for pilot
decisions rather than billing claims.

Deliver:

- provider usage and cost reports;
- generation latency and failure trends;
- per-school/user usage filters;
- manual versus AI adoption;
- quality/preflight and regeneration metrics;
- inactive-school and onboarding-funnel views;
- school health summary.

Exit criteria:

- the team can explain AI spend by school and action;
- repeated provider or subject failures are visible;
- metrics are reproducible from documented definitions;
- reports do not expose unnecessary private exam content.

### Phase 4 — Governance, security, and curriculum operations

Deliver:

- full audit centre;
- session/account controls;
- safe, time-limited support access;
- incident and alert workflow;
- curriculum/import operations;
- versioned curriculum edits and rollback;
- retention and redaction tooling;
- export/audit reports.

Exit criteria:

- every sensitive company action is attributable;
- support access is visible to the school and company;
- curriculum changes are reversible;
- critical alerts have acknowledgement and resolution history.

### Phase 5 — Commercial administration (deferred)

Only after pilot evidence supports it:

- plans and entitlements;
- trial cohorts;
- subscription state;
- billing integration;
- invoices and payment history;
- partner/API customer administration;
- feature flags and rollout controls;
- revenue and retention reporting.

Pricing decisions must not block Phases 0–4. Usage measurement and quota safeguards should be implemented independently of final pricing.

---

## Initial backlog by priority

### P0 — Required before internal MVP

- platform permission boundary;
- platform staff authentication;
- audit-event base model;
- school and user directory;
- queue/job monitor;
- health overview;
- bounded usage aggregates;
- tenant-isolation tests;
- redaction policy.

### P1 — Required for pilot support

- feedback submission;
- support ticket workflow;
- in-app notification inbox;
- unread bell/count;
- support assignment;
- critical email notifications;
- alert acknowledgement;
- mobile visual polish.

### P2 — Important for scale

- provider cost analytics;
- quality/product intelligence;
- daily rollups;
- curriculum operations;
- safe support access;
- incident records;
- retention tooling.

### P3 — Deferred commercial layer

- payment and invoicing;
- plan administration;
- partner/API customer console;
- revenue analytics;
- advanced feature rollout management.

---

## Success measures

The operating layer is successful when the company team can:

- detect a generation outage before multiple schools report it;
- identify the affected schools and users;
- see whether the cause is provider, queue, curriculum, storage, email, or application failure;
- acknowledge and communicate the incident;
- trace the complete history of important actions;
- receive and respond to pilot feedback in one place;
- measure whether a fix improved success rate and completion time;
- understand usage and AI cost without manually querying production;
- support schools without violating their privacy or weakening tenant isolation.

The guiding principle is **operational clarity without unnecessary bureaucracy**: the company team gets the visibility and controls required to operate SkuPhase, while teachers and school administrators keep autonomy over their actual educational work.
