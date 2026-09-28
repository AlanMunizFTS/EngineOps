# ADR 0010: Dynamic Kanban boards - multiple boards, customizable columns

## Status

Accepted. Supersedes the fixed-board/fixed-column decision in
[ADR 0004](0004-issue-hierarchy-linking.md).

## Context

ADR 0004 shipped one Kanban board per project with exactly 5 fixed columns,
each mapped 1:1 to an `IssueStatus` value, explicitly deferring
customization: "customizable columns are a later polish item." Sebastian now
wants that: multiple independent board views per project, each with
freely-named, freely-ordered columns he controls directly.

## Decision

**Card membership stays entirely status-driven - no placement table.**
`KanbanColumn.maps_to_status` (a single `IssueStatus`) becomes
`maps_to_statuses` (a Postgres array of `IssueStatus`, migration 0019). A
column shows every issue whose `status` is in its list:

- Zero statuses -> the column never shows a card (allowed - e.g. a
  placeholder while building out a new board).
- One status -> identical behavior to before.
- Multiple statuses -> aggregates them into one visual lane. Dragging a card
  into it sets the issue's status to the **first** entry in the list - a
  deliberate simplification over asking "which of these N statuses did you
  mean" on every drop.

This is the key design choice that keeps the change additive rather than a
rewrite: `Issue.status` remains the single source of truth for where a card
sits, so no new join table, no dual-write bookkeeping, and every existing
status-based feature (filters, audit trail, `schedule_status`) is untouched.
The tradeoff: a board's columns are a *view* over status, not an independent
per-board position - the same issue can't sit in different "custom" columns
on two boards if those columns cover the same status differently. That's an
acceptable limit for now; a true per-board placement table is the fallback
if it stops being one.

**A project can have any number of boards.** Drops the `unique` constraint
on `kanban_boards.project_id`. `create_default_board` still seeds one board
named "Board" with 5 single-status columns automatically on project
creation (`ADR 0004`'s original 5, unchanged) - nothing regresses for
existing projects. Additional boards created via `create_board` seed the
**same 5 default columns** rather than starting blank - a new board is
useful immediately (every existing issue lands somewhere) instead of
looking broken until the user manually configures columns. From there the
user renames, remaps, deletes, and adds columns freely via
`POST /kanban-boards/{id}/columns` and friends.

**Full CRUD surface**: create/list/rename/delete boards; create/update/
delete/reorder columns. `reorder_columns` takes the full ordered list of a
board's column IDs (not a single move-one-column op) - simpler to implement
and reason about, and matches how the frontend drag-and-drop already
computes the target order client-side.

## Consequences

- `GET /projects/{id}/kanban` (single board) is removed outright, replaced
  by `GET /projects/{id}/kanban-boards` (list) + `GET /kanban-boards/{id}`
  (one board) - pre-production, no deprecation window needed, consistent
  with this repo's established precedent (ADR 0005, ADR 0006, ADR 0009).
- The frontend's board switcher defaults to the first board (alphabetical)
  when a project has more than one.
- A column with an empty `maps_to_statuses` is a legal, inert state - the
  frontend surfaces this as a non-interactive drop target rather than
  silently failing on drop.
- Migration 0019's `downgrade()` collapses `maps_to_statuses` back to a
  single `maps_to_status` (taking the first element) and re-adds the
  one-board-per-project unique constraint - which will fail if a project
  has accumulated more than one board by then. Acceptable: downgrades in
  this repo have never promised to preserve data shapes introduced after
  the migration being reverted (see ADR 0009's downgrade note).
