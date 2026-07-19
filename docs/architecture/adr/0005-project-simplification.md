# ADR 0005: Project becomes a flat entity again; Phase pipeline reduced and moved into the tab bar

## Status

Accepted - supersedes [ADR 0003](0003-phase-inheritance.md) entirely, and
narrows [ADR 0004](0004-issue-hierarchy-linking.md)'s issue-linking decision
(the fixed-kanban-columns half of ADR 0004 still stands).

## Context

Phase 1 built `standard (project) > plant > machine > implementation` as a
four-level hierarchy, with phase-status inheritance cascading down it (ADR
0003) and Phase 2's issues linking flexibly into any level of it (ADR 0004).
Product direction changed: the platform doesn't need that hierarchy. A
project is tracked as a single flat entity.

Separately, the 9-phase pipeline from ADR 0002 (Scope, Analysis, Designs,
Approvals, Buys, Shipments, Development, Implementation, BuyOff) is more than
this platform needs right now, and living in a sidebar stepper undersells it
compared to the other project-level views (Issues, Kanban, Milestones) that
each get a full top-level tab.

## Decision

**Hierarchy removal:** `plants`, `machines`, and `implementations` tables,
entities, ports, adapters, routers, and UI are deleted outright (migration
0013). Nothing replaces them - a project has no sub-levels. Issues
(`issues.plant_id`/`machine_id`/`implementation_id` and their CHECK
constraint) drop back to linking only to `project_id`, exactly like the
original kickoff spec before the hierarchy existed.

**Phase pipeline reduction:** the 9 statuses collapse to **Scope, Analysis,
Stock, Development** (migration 0014) - Designs, Approvals, Shipments,
Implementation, and BuyOff are dropped as out of scope; Buys is renamed
Stock. The `project_areas`/`area_types`/`area_statuses` mechanism (ADR 0001)
is untouched - this is a reseed, same as ADR 0002's original migration.

**Phase pipeline relocation:** the phase selector moves out of
`ProjectPhasesSidebar` and into the same top-level tab bar as Code / Issues /
Kanban / Milestones / Settings - one tab per phase status, rendered
dynamically from `area_statuses` (not hardcoded) so a future phase is still a
data insert, not a frontend change. `PhaseToolsPanel` drops its
plant/machine/implementation "move into this phase" functionality (that
mechanism no longer exists) and becomes a simple current/set-as-current view
per phase.

## Consequences

- `ImplementationStatus` enum, `Plant`/`Machine`/`Implementation` entities,
  and every plant/machine/implementation-specific port, adapter, router,
  schema, and test are deleted, not deprecated - pre-production, no
  migration path needed (consistent with 0008/0009's precedent).
- Issue creation/update payloads no longer accept `plant_id`/`machine_id`/
  `implementation_id` - `IssueCreateRequest`/`IssueUpdateRequest` only carry
  `title`/`description`/`issue_type`/`priority`/`milestone_id`/`assignee_id`.
- The sidebar's Project > Plant > Machine > Implementation tree (`ProjectTree`,
  `ProjectPlants`, `ImplementationPhasePanel`) is deleted; the sidebar goes
  back to a flat project list.
- Migrations 0013 and 0014 both provide a full `downgrade()` that recreates
  the dropped tables/reseeds the old 9 statuses, matching this repo's
  established migration rigor - but neither recovers dropped data
  (pre-production, no real data at stake, same stance as every prior reseed).
