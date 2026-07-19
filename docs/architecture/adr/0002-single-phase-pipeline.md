# ADR 0002: Single flexible phase pipeline replaces per-domain area tracks

## Status

Accepted - supersedes the "why not a single field" framing in
[ADR 0001](0001-project-area-status-tracking.md), not its mechanism.

## Context

ADR 0001 modeled project progress as N independent per-domain area tracks
(Scope & Charter, Procurement, Electrical, Mechanical, Vision, Import/Export)
because a single project-wide status couldn't represent "procurement waiting on
material while electrical is mid-design while scope is awaiting signature."

In practice, Sebastian's team tracks a project's overall progress through one
shared pipeline of named phases - **Scope, Analysis, Designs, Approvals, Buys,
Shipments, Development, Implementation, BuyOff** - confirmed explicitly non-linear
and flexible (a project can move between phases out of order, not a strict
sequential gate). Fine-grained per-machine-instance tracking already exists
independently via `implementations.status` (planned/active/superseded/
decommissioned) and was never part of the area model - "el proyecto esté en una
etapa en general pero cada instancia en máquina puede tener su propio status."
The 6-domain-area model added a grid of simultaneous tiles that didn't match how
the team actually talks about where a project stands.

## Decision

Collapse the area catalog to a **single area_type** ("Phase") holding the 9
named statuses above, instead of 6 domain-specific area_types. The
`project_areas`/`area_types`/`area_statuses` mechanism built in ADR 0001 is kept
exactly as-is - non-linear, flexible, data-driven (a new phase is a data insert,
not a migration) - only the seed data changes. A project now has exactly **one**
`project_areas` row instead of 6.

No backend code changes were required beyond the migration: the ports, adapters,
and routers built in ADR 0001 already generalize over an arbitrary number of
area_types and statuses per area_type. This is purely a reseed.

## Consequences

- `ProjectAreaTiles` (frontend) becomes a single phase pipeline/stepper - the
  project's primary status indicator, not one tile among several. Renamed to
  `ProjectPhasePipeline`.
- The future AI PM assistant (see memory: ai-pm-assistant-scope,
  area-status-pipeline-idea) will live inside each phase - phase design and
  assistant design are now coupled.
- Migration 0009 drops the 6-domain seed and all existing `project_areas` rows
  (pre-production, no real data at stake), reseeds the single "Phase" area_type
  + 9 statuses, and backfills a "Scope" `project_areas` row for every existing
  project so the invariant "every project has exactly one project_areas row"
  holds without any application-level backfill logic.
- Implementation-level status is explicitly out of scope for this change - it
  stays a separate, independent concept on `implementations.status`.
