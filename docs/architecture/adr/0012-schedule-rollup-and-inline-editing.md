# ADR 0012: Schedule view - parent rollup, inline editing, drag-to-reparent, and Kanban visibility

## Status

Accepted. Follow-on from ADR 0011, which explicitly deferred parent date
rollup as a "future enhancement."

## Context

ADR 0011 shipped `parent_issue_id` subtasks but left three things unfinished
for the Schedule (Gantt) view, plus a UX gap that surfaced once subtasks
were in daily use:

1. A parent issue's own Gantt bar used only its own `start_date`/`due_date`
   - it never reflected when its children actually start and finish.
2. Only issues with a `due_date` appeared in the Schedule at all, so an
   unscheduled activity (or a parent with only unscheduled children) had no
   way to be seen or given dates from that view.
3. Reparenting an issue required going to its detail page and picking from
   a dropdown - no direct manipulation in the Gantt.
4. Once a parent issue's progress is represented by its children's rollup,
   it no longer makes sense for that parent to *also* carry its own status
   through a Kanban column - a card that never really "moves" because its
   real work lives in its subtasks.

## Decisions

**Parent bars roll up from descendants, computed frontend-only.**
`SchedulePage.tsx::buildEffectiveRanges` recursively computes, per issue,
`min(descendant starts)` -> `max(descendant dues)` and falls back to the
issue's own `start_date`/`due_date` only when it has no dated descendants
anywhere in its subtree. This mirrors the three-color bar decision in ADR
0011: no new API field, computed at render time from data already in
`IssueResponse`. A rolled-up bar renders as a thinner indigo segment
(`h-2`, distinct from the `h-4` blue/green/red plan-vs-actual bars) so a
summary row is visually distinguishable from a bar reflecting real
start/close dates. The parent's own `start_date`/`due_date` fields are
unchanged in storage and still editable - the rollup only wins when
descendants provide a range, consistent with "children are the source of
truth for a parent's schedule once it has any."

**Every issue appears in the Schedule now, dated or not.** The row list
(`buildScheduleRows`) is built from the full project issue set rather than
filtering to `due_date !== null` first; only the calendar's day-range
(`days`/`weeks`) still scans dated issues (there's nothing to plot a column
range from otherwise). Undated issues simply render with no bar segments.
Start/Due became `<input type="date">` cells and Title became an inline
text input - editable directly in the grid, consistent with the "activities
should be manageable from the timeline" ask. Responsible and Status are now
`<select>` cells too, wired through the same `updateIssue`/`updateIssueStatus`
calls the detail page uses, including the same done-confirmation modal
(ADR 0011) when Status is set to `done` from this view.

**Rows are collapsible, expanded by default.** A disclosure arrow appears
on any row with children (`ScheduleRow.hasChildren`); collapsing a row
skips recursing into its children in `buildScheduleRows` rather than hiding
them with CSS, so collapsed subtrees don't affect the calendar's day range
or add DOM nodes. State is a local `Set<string>` of collapsed issue IDs,
not persisted - it's view state, not data.

**Drag-and-drop reparents.** Each row's `#`/index cell is both a drag
source and a drop target (`@dnd-kit`, same library as the Kanban board).
Dropping issue A onto issue B sets `A.parent_issue_id = B.id`. A
`isDescendantOrSelf` guard rejects drops that would create a cycle (you
can't drop a task onto its own descendant) - client-side only, matching
ADR 0011's decision not to enforce cycle detection server-side in v1. A
small "x" next to a child's title clears `parent_issue_id` directly for the
common "un-nest this" case without needing a drag gesture.

**A "New activity" button creates issues directly from the Schedule**,
optionally with start/due dates, using the existing `createIssue` endpoint
- no new API surface.

**Parent issues no longer appear on Kanban boards.** `KanbanBoard.tsx`
computes the set of issue IDs referenced as someone's `parent_issue_id` and
excludes them before grouping cards into columns. Rationale: once a parent's
schedule is a rollup of its children (this ADR) and its real work is
tracked at the subtask level, its own `status` isn't a meaningful signal for
a board - showing it as a card that never naturally moves is more confusing
than useful. This is a `KanbanBoard`-level filter (derived from `issues`
already passed as a prop), not a backend change - a parent issue still has
a real `status`/`IssueResponse` like any other issue, it's simply not
projected onto Kanban.

## Consequences

- No new database columns, migrations, or API fields - everything in this
  ADR is either frontend computation (rollup, day-range) or reuses existing
  mutation endpoints (`updateIssue`, `updateIssueStatus`, `createIssue`).
- A parent's Schedule row shows the rollup range even if the user also set
  its own `start_date`/`due_date` explicitly - those stored fields become
  effectively dormant for display purposes as soon as it has any dated
  descendant. This can read as surprising if someone expects their manual
  parent dates to win; documented here rather than hidden.
- `urgency`/`priority_score`/`schedule_status`/`days_planned` are **not**
  rolled up - they remain computed server-side from the issue's own stored
  dates (ADR 0009), so a parent with a rolled-up Gantt bar can still show a
  blank Score/Status in the Schedule's own columns if it has no dates of its
  own. Rolling the priority engine up through children is a further
  possible enhancement, deliberately out of scope here.
- A project with zero dated issues still renders the Schedule grid (a
  minimal one-week range around today) so undated activities and the
  "New activity" button are always reachable, not gated behind having at
  least one dated issue.
- Excluding parents from Kanban is a view-layer decision only - parent
  issues keep a real `status` and can still be found via Issues list
  filters; they just won't render as cards. If a workflow needs a parent to
  be Kanban-visible again, the fix is removing its last child link, not a
  config flag (none was added - keeping this additive and simple per this
  session's established pattern).
