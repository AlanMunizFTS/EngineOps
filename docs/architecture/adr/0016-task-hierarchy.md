# ADR 0016: Project, Milestone, Task and Subtask Hierarchy

## Status

Accepted. Supersedes the active project-tracking decisions in
[ADR 0004](0004-issue-hierarchy-linking.md),
[ADR 0011](0011-issue-subtasks-and-history.md),
[ADR 0012](0012-schedule-rollup-and-inline-editing.md),
[ADR 0013](0013-issue-deletion-and-closed-at.md), and
[ADR 0014](0014-parent-assigned-at.md). It also supersedes migration 0024's
removal of Milestones; unrelated project-flattening decisions remain historical.

## Context

The Issue model accumulated recursive parent links, Schedule-specific
behavior, a Kanban rule that exposed leaf Issues, and eventually the removal
of Milestones. That combination no longer matches how EngineOps work is
planned and executed. The product needs one explicit, bounded hierarchy:

```text
Project
└── Milestone
    └── Task
        └── Subtask
```

A Task may also belong directly to a Project without a Milestone. Arbitrary
nesting, Epics, Features, Stories, and Sub-subtasks are outside the model.

Existing project-tracking data is disposable during this refactor. The
authentication domain is not: user identities, password hashes, account
status, roles, and role assignments must survive the schema rebuild.

## Decision

### Ownership and hierarchy

- A Project is the root and owns Milestones and Tasks.
- Milestones are organizational containers. They never appear as Kanban
  work cards.
- Tasks are executable top-level work.
- Subtasks are direct children of Tasks and cannot contain children.
- Tasks and Subtasks use the same `tasks` table. There is no separate
  Subtask entity or table.
- `parent_task_id IS NULL` means Task; `parent_task_id IS NOT NULL` means
  Subtask. Nested Subtasks, self-parenting, cycles, and cross-project
  parenting are forbidden.
- `task_type` classifies work (`task`, `bug`, `improvement`, or `incident`);
  it does not determine hierarchy.

Only top-level Tasks may store `milestone_id`. A Subtask stores
`milestone_id = NULL` and inherits its parent's Milestone logically. Deleting
a Milestone sets its Tasks' `milestone_id` to null rather than deleting work.
Milestone progress counts completed top-level Tasks over all top-level Tasks;
Subtasks do not enter that denominator.

### Execution views and invariants

Project Kanban and My Kanban show top-level Tasks only. Subtasks are managed
inside Task Detail and never appear as independent Project Kanban cards.
Schedule displays at most Task → Subtask and may roll dates up from direct
children only.

Hierarchy and completion rules live in the application service layer, not
in FastAPI routes, SQLAlchemy repositories, or React. In particular:

- a Task cannot complete while any Subtask is incomplete;
- an incomplete Subtask cannot be created under, or reopened beneath, a
  completed parent;
- a Task with children cannot become a Subtask or be deleted; and
- parent assignment and reparenting require a top-level Task in the same
  Project.

Database constraints provide defense in depth for self-parenting and for
the rule that Subtasks cannot store a Milestone. Application validation is
still authoritative for rules requiring graph queries.

### Schema reset and authentication boundary

Migration 0027 replaces the active `issues`, `issue_labels`, and
`issue_comments` schema with `tasks`, `task_labels`, and `task_comments`,
reintroduces `milestones`, and changes Kanban status mappings from
`issue_status[]` to `task_status[]`. Old project-owned rows are intentionally
discarded rather than translated.

The preserved authentication dependency graph is:

```text
users ──< user_roles >── roles
  │
  ├── projects.created_by          (disposable reference)
  ├── project_members.user_id      (disposable reference)
  ├── tasks.assignee_id            (new disposable reference)
  ├── tasks.created_by             (new disposable reference)
  ├── task_comments.author_id      (new disposable reference)
  ├── audit_log.actor_id           (disposable reference)
  └── file_tree_nodes.created_by   (disposable reference)
```

`users`, `roles`, and `user_roles` are never dropped, recreated, truncated,
or reseeded by the reset. Therefore user IDs, emails, password hashes,
`is_active`, role IDs, and role assignments remain unchanged. Rows owned by
Projects may be deleted safely even when they reference a preserved User.

Historical migrations remain immutable. Historical ADRs remain available
to explain the schema that existed before revision 0027.

## Consequences

- EngineOps has one vocabulary and one bounded work hierarchy: Project →
  Milestone → Task → Subtask.
- Task Detail becomes the execution surface for Subtasks; Kanban remains a
  top-level planning surface.
- Recursive Schedule algorithms and leaf-only Kanban behavior are removed.
- Existing Issue IDs, comments, labels, history, Milestones, boards, and
  other project data are not migrated. Operators must treat migration 0027
  as a project-data reset.
- Upgrade and downgrade can both reconstruct their respective schemas, but
  neither direction restores discarded project data.
- Migration verification must snapshot and compare users, password hashes,
  roles, and `user_roles` across upgrade, downgrade, and re-upgrade.
