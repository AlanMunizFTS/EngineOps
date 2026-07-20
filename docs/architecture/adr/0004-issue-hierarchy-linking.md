# ADR 0004: Issues link flexibly to one hierarchy level; kanban columns are fixed for now

## Status

Partially superseded by [ADR 0005](0005-project-simplification.md): the
hierarchy the issue-linking half of this decision depended on
(plant/machine/implementation) no longer exists, so issues now link only to
`project_id`. The fixed-kanban-columns half of this decision still stands.

## Context

The Phase 2 kickoff spec (written before ADR 0002/0003 introduced the
`standard (project) > plant > machine > implementation` hierarchy) defined
`issues.implementation_id` as a single nullable FK. That no longer matches the
data model: an issue can just as usefully describe a plant-wide rollout
problem or a machine-level defect as an implementation-specific bug, and
forcing every non-implementation issue up to `implementation_id = NULL` would
throw away real information the hierarchy now carries.

Separately, the spec described `kanban_columns` as "customizable per project."
Building column CRUD/reordering now, before any project has exercised the
default 5-column board, is speculative - YAGNI until there's a concrete
customization request.

## Decision

**Issue linking:** `issues` gets three nullable FKs - `plant_id`, `machine_id`,
`implementation_id` - instead of one. A CHECK constraint enforces **at most
one** is non-NULL at a time:

```sql
CHECK (
  (plant_id IS NOT NULL)::int
  + (machine_id IS NOT NULL)::int
  + (implementation_id IS NOT NULL)::int <= 1
)
```

All three NULL means the issue is project-wide. `project_id` is always set
directly on the row (not derived through the link) so project-scoped queries
never require a conditional join through whichever level is populated.

**Kanban columns:** `kanban_boards`/`kanban_columns` tables are built now (per
the original data model) and one board with 5 fixed columns - Backlog, To Do,
In Progress, In Review, Done, each `maps_to_status` one of the 5 `IssueStatus`
values - is seeded automatically per project (on creation, and backfilled for
projects that predate this migration). There is no column create/rename/
reorder API in Phase 2. Moving a card between the fixed columns updates
`issues.status` directly via `PATCH /issues/{id}/status`.

## Consequences

- `issues` denormalizes `project_id` alongside the optional link, same
  trade-off the audit_log already makes (kickoff spec §4) - fast per-project
  queries without a conditional join.
- Application code must set at most one of the three link fields; the CHECK
  constraint is the backstop against a bug doing otherwise, not the primary
  guard (the create/update issue endpoints validate this too, so the error is
  a 422 rather than a raw DB constraint violation reaching the client).
- Because `maps_to_status` is unique per board today (one column per status),
  the kanban board view can be built directly from `IssueStatus` if the
  `kanban_columns` read is ever skipped - but the API always returns the
  actual seeded columns, not the enum, so a future customization (renaming a
  column, hiding one) doesn't require a frontend contract change.
- Real column customization (add/remove/reorder, N:1 status mapping) is
  deferred; if requested, it lands as new endpoints on the existing
  `kanban_columns` table, not a schema change.
