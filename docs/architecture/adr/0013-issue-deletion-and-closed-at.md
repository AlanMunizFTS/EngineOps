# ADR 0013: Issue deletion, manually-correctable closed date, and no score once done

## Status

Superseded by [ADR 0016](0016-task-hierarchy.md).

## Context

Three related gaps surfaced once issues, subtasks, and the Schedule rollup
(ADR 0011, ADR 0012) were in daily use:

1. There was no way to remove an issue at all - created by mistake, a
   duplicate, or test data - short of manipulating the database directly.
2. `closed_at` was only ever set automatically by `set_status` (ADR 0009),
   with no way to correct it - useful when backfilling historical issues or
   fixing a close date that was set by accident.
3. `priority_score` (ADR 0009) kept being computed for `done` issues even
   though urgency/priority no longer mean anything once the work is
   finished - a completed task showing a "10" priority score reads as if it
   still needs attention.

## Decisions

**Issues can be deleted from the project's Settings tab.** `Settings` was
previously a disabled "coming soon" tab (`ProjectTabs.tsx`); it's now a real
page (`SettingsPage.tsx`) listing every issue in the project with a delete
action, confirmed via `window.confirm` - the same lightweight confirmation
pattern already used for Kanban board/column deletion, not the `Modal`
component (that's reserved for the done-transition confirmation per ADR
0011; deleting from a dedicated Settings list is already a deliberate,
out-of-the-way action). `IssueRepository.delete()` is a new port method; the
SQLAlchemy adapter issues a plain ORM delete and lets Postgres's existing
`ON DELETE CASCADE` (issue_comments, issue_labels) and `ON DELETE SET NULL`
(child issues' `parent_issue_id`) foreign keys do the rest - consistent with
ADR 0011's decision that deleting a parent orphans its children rather than
cascading the delete to them.

**`closed_at` is editable through the general update endpoint.**
`IssueUpdateRequest`/`IssueRepository.update()` gained an optional
`closed_at: date` field, alongside the existing `start_date`/`due_date`.
It's a manual correction, separate from the automatic stamping
`set_status` still does when an issue actually transitions to/from `DONE` -
the two are independent write paths, same as how `days_planned` and
`set_status`'s automatic `closed_at` don't interfere with each other. On the
Issue detail page, "Closed date" sits next to Start/Due date in the
Schedule section - a plain date input, not gated on `status == done`, since
the deployment intent is "let me backfill or fix this timestamp for
whatever reason," not "only after this issue is done."

**`priority_score` is `null` once an issue is `done`.** `_issue_response`
now short-circuits to `None` instead of calling `calculate_priority_score`
when `status == IssueStatus.DONE`. `urgency` is left as-is (still computed
from `due_date`) since it's descriptive rather than an action signal, and
suppressing it wasn't asked for - only the score, which is what drives
attention/ordering. The Schedule table and Issue detail page both already
guard `priority_score !== null` before rendering `PriorityScoreChip`, so a
done issue's score cell/badge simply disappears with no frontend change
required beyond the backend computation change.

## Consequences

- No new migration - `closed_at` was already a column; deletion needs no
  schema change, only a new port method and the FK `ondelete` behavior
  already in place from ADR 0011.
- Deleting an issue is irreversible in this UI (no soft-delete / trash).
  Consistent with this repo's established pre-production stance (ADR 0005,
  0006, 0009, 0010) of preferring simple, destructive operations over
  reversibility machinery until real data is at stake.
- A `done` issue's `priority_score` going to `null` is a breaking response
  shape change for any code reading it as always-numeric-or-null-only-when-
  no-due-date; the two call sites in this codebase already null-guard, but
  this is worth remembering if `priority_score` is consumed anywhere new.
- Manually setting `closed_at` does **not** change `status` - an issue can
  have a `closed_at` date while still `status: in_progress`, which will
  make `schedule_status` report `closed` (ADR 0009's
  `calculate_schedule_status` keys off `closed_at`, not `status`) even
  though the issue isn't actually `done`. This is an accepted edge case of
  treating the two fields as independently editable rather than coupling
  them with validation - documented here rather than silently allowed to
  surprise someone later.
