# ADR 0009: Project Schedule (Gantt) view — Urgency, Importance, and Priority Score

## Status

Accepted.

## Context

Sebastian tracks per-activity schedules today in an Excel Gantt template:
a left-hand table (Activity, Stage, Responsible, Start Date, Days Planned,
Due Date, Days Taken, Status, Close Date, Notes) plus a weekly grid with
colored bars per activity. He wants that view inside the app, on top of the
existing `Issue` model, with two priority signals combined into a single
sortable rank:

- A **static** priority a person assigns and rarely changes (already modeled
  as `IssuePriority`: Low/Medium/High/Urgent).
- A **time-pressure** priority that should drift automatically as the due
  date approaches, counting only working days (Mon-Fri) — a task due
  tomorrow is more pressing today than it was a week ago, with no one
  needing to re-triage it by hand.

## Decision

**Extend `Issue`, don't introduce a new entity.** `stage`, `start_date`,
`due_date`, and `days_planned` are added as nullable columns on `issues`
(migration 0018). An issue with no `start_date`/`due_date` simply doesn't
appear on the Schedule view — everything else about it (Kanban, comments,
labels) is unaffected. `Stage` is a free-text field for now (e.g.
"Collection", "Cut", "Inspector Validation") — it does not feed the Kanban
board's fixed five columns; customizable/multiple Kanban boards are a
separate, later piece of work.

**Two named priority signals, borrowing Eisenhower-matrix terminology**
because it already fits:

- **Importance** — the existing `IssuePriority` (Low/Medium/High/Urgent),
  assigned by a person, unchanged in the schema or API. Referred to as
  "Importance" only in Schedule-view UI copy.
- **Urgency** — new, computed, never stored: `Low`/`Medium`/`High`, derived
  from working days remaining until `due_date` as of the moment it's read.
  `0` working days left (due today or overdue) → `High`; `1` → `Medium`;
  `2+` → `Low`. Saturdays/Sundays never count as a working day in this
  calculation (`domain/scheduling.py`).
- **Priority Score** — the 1-10 composite PMs actually sort by:
  `score = urgency_rank(0-2) * 3 + importance_rank(1-3)`, giving a 3x3 grid
  of scores 1-9 across Urgency x Importance, except **Importance = Urgent
  always scores 10** regardless of Urgency (an urgent item is always top of
  the list, full stop).

  | Urgency \ Importance | Low | Medium | High |
  |---|---|---|---|
  | Low | 1 | 2 | 3 |
  | Medium | 4 | 5 | 6 |
  | High | 7 | 8 | 9 |

  Importance = Urgent → 10, independent of the row above.

**Computed at request time, not stored.** `Urgency`, `Priority Score`,
`days_taken` (working days elapsed since `start_date`, up to today or
`closed_at`), and `schedule_status` (`closed` / `on_time` / `late`) are all
derived from `date.today()` in `IssueResponse` construction
(`api/routers/issues.py::_issue_response`) — storing any of them would go
stale the moment a day passes without that row being written to.

**Pure domain module, no port needed.** `domain/scheduling.py` has zero I/O
and zero dependencies beyond `IssuePriority` — it's a set of deterministic
functions of `(today, due_date, ...)`, so it doesn't need a Port/Adapter
pair; it's imported directly by the router, same as any other domain
calculation.

## Consequences

- `IssueCreateRequest`/`IssueUpdateRequest` gain four optional fields
  (`stage`, `start_date`, `due_date`, `days_planned`); nothing existing
  breaks since all four default to `None`.
- The Schedule (Gantt) tab reads the same `/projects/{id}/issues` endpoint
  as Issues/Kanban — no new CRUD surface, just new fields on the existing
  response and a new frontend view over it.
- Sorting/filtering by `priority_score` happens client-side for now (the
  field isn't indexed or queryable via the list endpoint) — revisit if a
  project's issue count makes that a real cost.
- Named "Schedule" in the tab bar, not "Timeline" — "Timeline" already names
  the project's audit-log/activity-feed view (`ProjectTimeline.tsx`,
  `GET /projects/{id}/timeline`); reusing it here would collide in meaning.
- Deferred, explicitly out of scope here: customizable/multiple Kanban
  boards (dynamic columns, more than one board per project) — a separate
  overhaul of the Kanban feature, not bundled into this change.
