# ADR 0006: Remove the Phase pipeline; rename the Code tab to Dashboard

## Status

Accepted - supersedes the phase-pipeline portions of [ADR 0001](0001-project-area-status-tracking.md),
[ADR 0002](0002-single-phase-pipeline.md), and [ADR 0005](0005-project-simplification.md).
The hierarchy-removal and flat-project decisions in ADR 0005 stand unchanged.

## Context

ADR 0005 reduced the original 9-status Phase pipeline (ADR 0002) to four -
Scope, Analysis, Stock, Development - and moved it from a sidebar stepper
into the top-level project tab bar, one tab per status. Product direction
narrowed further: the platform doesn't need a phase-tracking concept at all
right now. Keeping it would mean shipping three of the four tabs (Scope,
Analysis, Development) with no content beyond a placeholder "AI-guided tools
coming soon" panel, and the fourth (Stock) has no defined purpose on its own
once decoupled from the pipeline it belonged to.

Separately, the project's base tab (`Code`, a GitHub-style default view) is
being renamed to `Dashboard` to describe what it actually shows.

## Decision

**Phase pipeline removal:** the `area_types`/`area_statuses`/`project_areas`
mechanism (ADR 0001) is dropped entirely - tables, entities, ports, adapters,
schemas, routers (`/catalog/area-types*`, `/projects/{id}/areas*`), and the
frontend `PhasePage`/`PhaseToolsPanel`/`/projects/:id/phase/:statusId` route
are all deleted outright (migration 0015). Nothing replaces it. The project
tab bar goes back to a fixed, non-data-driven set of tabs.

**Tab rename:** `Code` becomes `Dashboard` in `ProjectTabs.tsx`. No routing or
content change - `ProjectDetailPage` still renders at the project's base
route (`/projects/:projectId`).

Resulting tab bar: **Dashboard | Issues | Kanban | Milestones | Settings**.

## Consequences

- `AreaType`/`AreaStatus`/`ProjectArea` entities, `AreaRepository` port,
  `SqlAlchemyAreaRepository` adapter, and the `catalog` router are deleted,
  not deprecated - pre-production, no migration path needed (consistent with
  0008/0009/0013's precedent).
- `POST /projects` no longer calls `create_default_areas` - project creation
  now only seeds the owner membership and the default Kanban board.
- Migration 0015 provides a full `downgrade()` that recreates the
  `project_areas`/`area_statuses`/`area_types` tables and reseeds the four
  ADR 0005 statuses, matching this repo's established migration rigor - but
  does not recover dropped data (pre-production, no real data at stake).
- If phase/status tracking is needed again later, it should be scoped and
  designed fresh against actual product requirements rather than resurrecting
  this mechanism.
