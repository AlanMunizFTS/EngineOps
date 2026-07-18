# ADR 0001: Per-area project status tracking instead of a single project status

## Status

Accepted

## Context

The Phase 1 kickoff scope originally implied a single `projects.status` field. In
practice, a controls/vision engineering project does not move through one linear
status: procurement can be waiting on material while electrical is mid-design while
the scope & charter is still awaiting signature. A machine itself may not even exist
yet - it can be an output the project produces (designed and built), not a
precondition for the project to start. A single enum column cannot represent this
without either lying (picking one "dominant" status) or becoming an unbounded set of
compound states.

## Decision

Model project progress as multiple independent tracks instead of one field:

- `area_types` - a lookup table of tracked areas (Scope & Charter, Procurement,
  Import/Export, Electrical, Mechanical, Vision). Adding a new area is a data insert,
  not a schema migration.
- `area_statuses` - a lookup table of valid statuses, scoped per `area_type_id` (e.g.
  Procurement's vocabulary includes "Awaiting Material"; Scope & Charter's includes
  "Awaiting Signature"). New statuses are also a data insert.
- `project_areas` - one row per `(project_id, area_type_id)`, each with its own
  `status_id`, `updated_by`, `updated_at`. Created automatically (one per seeded
  `area_type`) when a project is created.

Every status change on a `project_areas` row fires the same `audit_log` hook as every
other write in this phase, so the project timeline (Phase 2) is where areas
"communicate" - a chronological, cross-area view of what changed and when, without a
second source of truth.

`machines` requires no schema change to support "the machine doesn't exist yet":
`machines.project_id` already makes a machine an optional, project-scoped child; a
project can have zero machines while still in Scope & Charter.

## Consequences

- No `projects.status` column. Any UI or query wanting "the" project status must
  either render all areas (the intended UX - area status tiles on the project detail
  page) or pick an aggregation rule explicitly (e.g. "any area Blocked" -> project
  flagged) rather than reading a field that doesn't exist.
- Adding a new area or status is a data change, not a migration - lower friction, but
  also less type safety than a native enum; validation of "is this status_id valid for
  this area_type_id" is enforced at the application/repository layer, not the database
  schema.
- Explicitly out of scope for this decision: an "AI PM" that reasons over area state
  and the audit log to proactively assist. That is a future agent living in its own
  bounded context per CLAUDE.md §10 (versioned prompts, human-in-the-loop checkpoints
  before any write), not part of this phase. This ADR only establishes the data model
  such an agent would eventually read.
