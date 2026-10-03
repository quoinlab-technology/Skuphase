# Pilot privacy and retention policy

SkuPhase stores school account records, teacher-authored assessment content,
curriculum selections, audit comments, lesson plans, and operational logs.
The free pilot should not store student names, student identifiers, fees, or
health information in the assessment workflow.

- School data is tenant-scoped by `school_id` on every operational record.
- Access is role-based; administrators control staff and approval actions.
- Generated documents inherit the owning school and must not be shared publicly.
- Retain pilot content for the current academic term plus 90 days for feedback.
- Remove or export content on a school's written request.
- Retain security and audit logs for 12 months, then delete or anonymize them.
- Backups follow the runbook retention period and are encrypted at rest.

Before public launch, obtain formal legal review, a data-processing agreement,
and a documented deletion/export workflow.
