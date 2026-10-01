# ADR 0011: Issue subtasks, computed days_planned, status history, and Gantt schedule-variance bars

## Status

Superseded by [ADR 0016](0016-task-hierarchy.md).

## Context

Follow-on from ADR 0009/0010. Four related changes to the Schedule/Issues
surface:

1. `stage` (free-text) is redundant now that Kanban columns are dynamic and
   freely named (ADR 0010) - the same grouping need is better served there.
2. `days_planned` was a manually-entered number that could silently drift
   from `start_date`/`due_date` once either changed.
3. There was no way to see an issue's status history - only its current
   `status` and `closed_at`.
4. Moving a card to "Done" had no confirmation step, and the Schedule Gantt
   bar only showed the plan, never how actual completion compared to it.
5. Activities need a parent/child structure (e.g. "Mushroom Validation" >
   "Wrinkle" > "Collect") reflected in the Schedule view.

## Decisions

**`stage` is removed** (migration 0020, column dropped). Grouping now
happens via Kanban boards/columns instead.

**`days_planned` becomes computed, not stored** (column dropped in the same
migration). `domain/scheduling.py::calculate_days_planned(start_date,
due_date)` counts working days with **both endpoints inclusive** - a task
starting and due the same weekday is "1 day planned," not 0 (deliberately
different from `days_taken`, which is start-exclusive since it measures
elapsed progress, not budgeted span). Always recomputed in `IssueResponse`,
same pattern as `urgency`/`priority_score`/`schedule_status`.

**Status history reuses the audit log - no new table.** Every status change
already writes an `issue.status_changed` audit entry
(`api/routers/issues.py::update_issue_status`, unchanged). What was missing
was a way to read it back scoped to one issue:
`AuditLogRepository.list_for_entity(entity_type, entity_id)` (new port
method) backs `GET /issues/{id}/history`. This mirrors the project timeline
(`list_for_project`) - same table, narrower filter, consistent with the
kickoff spec's stance that the audit log is the one feed, not a second
source of truth.

**Subtasks via `parent_issue_id`** (nullable, self-referential FK on
`issues`, `ON DELETE SET NULL` - migration 0020). Deleting a parent orphans
its children rather than cascading, since a child issue's own work is real
regardless of whether its parent still exists. This is deliberately a
*light* hierarchy (one FK, arbitrary depth via repeated self-reference) -
not the plant/machine/implementation hierarchy ADR 0005 removed. That one
was a fixed, project-wide structural ladder; this is an optional, per-issue
relationship, closer to GitHub/Jira sub-issues than to a domain hierarchy.
No cycle detection is enforced server-side yet (v1 scope) - the frontend's
parent picker only excludes the issue itself, not deeper descendants.

**Gantt bars show plan vs. actual, three colors.** For a still-open issue,
the bar is a single segment (`start_date` -> `due_date`), colored blue
(on time) or red (already overdue) - unchanged from ADR 0009. For a
**closed** issue, the bar splits at `due_date`:

- Closed on or before `due_date`: blue segment `start_date` -> `closed_at`
  (the actual working period), plus a **green** segment `closed_at` ->
  `due_date` (time saved).
- Closed after `due_date`: blue segment `start_date` -> `due_date` (the
  original plan), plus a **red** segment `due_date` -> `closed_at` (the
  overrun).

This is a frontend-only rendering decision (`SchedulePage.tsx`) - no new API
fields; `start_date`, `due_date`, `closed_at`, and `schedule_status` already
carry everything needed to derive it.

**Confirm before closing.** Setting status to `done` - from the Issue detail
page's status dropdown, or dragging a card into a Kanban column mapped to
`done` - now opens a confirmation modal before the status change is sent.
This is the first modal in the app (`components/Modal.tsx`, a small
reusable overlay+card, styled to match the rest of the UI) - introduced
here rather than earlier because this is the first destructive-ish,
worth-confirming action in the app (closing work is easy to do by accident
via drag-and-drop).

## Consequences

- `IssueCreateRequest`/`IssueUpdateRequest` drop `stage`/`days_planned`,
  gain `parent_issue_id`. `IssueResponse` drops `stage`, gains
  `parent_issue_id`; `days_planned` stays in the response shape but is now
  always server-computed.
- The Schedule table's "Stage" column is removed; the "Activity" column
  instead shows indentation + hierarchical numbering (1, 1.1, 1.1.1) derived
  from `parent_issue_id`.
- A parent issue's own Gantt bar uses its own `start_date`/`due_date` if
  set - it does **not** auto-aggregate its children's date range. Rolling up
  a parent's plan from its children's actual dates is a reasonable future
  enhancement, deliberately out of scope here to keep this change additive.
- `GET /issues/{id}/history` returns the full audit trail for that issue
  (not just status changes) - label attach/detach and field edits show up
  too, which is a feature, not noise: it's one place to see everything that
  happened to an issue.
