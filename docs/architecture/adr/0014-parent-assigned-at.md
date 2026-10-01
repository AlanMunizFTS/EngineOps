# ADR 0014: `parent_assigned_at` - sibling order survives re-linking

## Status

Superseded by [ADR 0016](0016-task-hierarchy.md). The useful
`parent_assigned_at` ordering concept is retained for Tasks, but the Issue
architecture described here is no longer active.

## Context

Reported bug: link issue A to a parent, realize B should actually come
first, unlink A, link B, then re-link A. Because Schedule sibling numbering
(ADR 0012) sorted children by `created_at`, A - created before B - always
numbered first regardless of how the user actually ordered them through the
UI. The fix needs to distinguish "when was this issue created" from "when
did it most recently become a child of this parent."

## Decision

Added `parent_assigned_at: datetime | None` to `Issue`, stamped by
`IssueRepository.update()` (and `.create()` for issues created with a
parent already set) whenever the resolved `parent_issue_id` differs from
what's currently stored - set to `now()` when a parent is assigned,
cleared to `None` when unset. This is caller-invisible, the same pattern
`set_status` already uses for `closed_at`: `IssueUpdateRequest` didn't grow
a new field, the repository just compares old vs. new `parent_issue_id`
internally and stamps accordingly.

`SchedulePage.tsx::buildScheduleRows` now sorts **root**-level activities by
`created_at` (unchanged - there's no "became a child" event for something
with no parent) but sorts **children** by `parent_assigned_at ?? created_at`
(the fallback covers rows persisted before this migration, which have
`NULL`). Practical effect: unlink A, link B, re-link A -> A's
`parent_assigned_at` is now later than B's, so B numbers first (`1.1`) and A
second (`1.2`), matching the order the user actually assigned them in,
not their original creation order.

## Consequences

- New nullable column, migration 0021, plain `ADD COLUMN` - no backfill,
  existing rows read as `NULL` and fall back to `created_at` exactly as
  before this change.
- Deleting a parent issue (ADR 0013) orphans its children via Postgres's
  `ON DELETE SET NULL` on `parent_issue_id`, but a FK action can't touch a
  second column - an orphaned child's `parent_assigned_at` is left stale
  pointing at whenever it was linked to the now-deleted parent. This is
  harmless: once `parent_issue_id` is `NULL` the issue is a root, and roots
  sort by `created_at`, never `parent_assigned_at`. The in-memory test fake
  clears it anyway for cleanliness, but the SQL adapter deliberately doesn't
  bother - not worth an extra query for a value that's provably unused once
  orphaned.
- Only the Schedule view's sibling ordering reads this field today. It's
  exposed on `IssueResponse` in case another surface needs "recently
  attached" ordering later, but nothing else consumes it yet.
