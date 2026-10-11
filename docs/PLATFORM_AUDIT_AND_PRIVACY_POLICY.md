# Platform audit and privacy policy

This policy closes the Phase 0 operating-layer contract. The internal console
must provide operational traceability without becoming a back door into school
content.

## Access matrix

| Capability | Owner | Admin | Support | Analyst | Content operator |
| --- | --- | --- | --- | --- | --- |
| Overview, schools | Read/write | Read/write | Read | Read | Read |
| Support cases | Full | Full | Assigned/support actions | Read | No access |
| Audit events | Read | Read | No access by default | Read | No access |
| Usage and provider metrics | Full | Read | Read | Read | No access |
| Curriculum operations | Full | Read | No access | Read | Full |
| Membership management | Full | Delegated | No access | No access | No access |

Platform membership is explicit, active, and separate from school roles. A
school administrator, school owner, email-domain holder, or support URL alone
does not grant platform access.

## Audit event contract

Important mutations record actor, role, school scope, action, target, result,
request correlation ID, and sanitized metadata. Tokens, passwords, full prompts,
attachments, and raw private exam content are never placed in event metadata.
Events are exposed through a bounded, read-only API and the internal audit
viewer; there is no application update endpoint for existing events.

The initial event taxonomy includes platform support status changes, support
assignment/replies/notes, and school feedback submission. Authentication,
invitation, settings, export, logo, and account events are the next additions
to the same service and do not change the access boundary.

## Retention and redaction

- Keep audit events for the active pilot and a documented post-pilot review
  period; retention execution will be added with the Phase 4 governance tools.
- Keep only operational summaries and stable entity IDs.
- Redact credentials, bearer tokens, reset links, passwords, model prompts,
  generated answer content, and uploaded file contents.
- Support access to raw school content requires a separate, time-limited,
  audited workflow; it is not enabled by this Phase 0 foundation.
- All audit exports must themselves create an audit event.

## Phase 0 exit criteria

- Platform endpoints have explicit membership/role dependencies.
- Tenant-facing users are denied platform routes.
- Audit storage, request correlation, redaction, bounded querying, and a
  read-only viewer exist.
- The remaining event hooks are tracked rather than silently forgotten.
