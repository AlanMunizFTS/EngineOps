# ADR 0003: Plant/Machine/Implementation inherit Phase from their parent unless overridden

## Status

Superseded by [ADR 0005](0005-project-simplification.md): Plant, Machine, and
Implementation were removed entirely, so there is nothing left to inherit a
phase override. Kept here for historical context only.

## Context

ADR 0002 gave each **project** a single Phase (Scope, Analysis, Designs,
Approvals, Buys, Shipments, Development, Implementation, BuyOff). In practice a
project's plants, machines, and implementations don't always move in lockstep -
one plant's rollout can be in Development while another is still Awaiting
Approval - but defaulting every plant/machine/implementation to track its own
independent Phase (a full `project_areas`-style row per node) would mean most
of them just duplicate the parent's value with no actual deviation, and would
require the UI to ask "what phase is this?" at every level before it's ever
useful.

## Decision

`plants`, `machines`, and `implementations` each get a single nullable
`phase_status_id` column (FK to `area_statuses`, same table ADR 0002 already
uses for the 9 phases - no new catalog).

- `NULL` (the default): this node **inherits** its parent's effective phase.
  Plant inherits from Project; Machine inherits from Plant's effective phase;
  Implementation inherits from Machine's effective phase. Resolution cascades
  down, computed client-side from an already-fetched tree (no server-side
  "effective phase" endpoint needed) - `effectivePhase(node) = node.phase_status
  ?? effectivePhase(parent)`.
- Non-`NULL`: an explicit **override** - this node's phase deliberately
  deviates from what it would otherwise inherit.

The UI marks an override with a small "M" badge (VSCode git-status-style),
matching the file-tree metaphor the sidebar and project detail page already
use. No override = clean/inherited, no badge.

## Consequences

- No new tables, no duplicated per-node area_type/area_statuses catalog -
  reuses ADR 0002's single "Phase" catalog directly.
- `PATCH /plants/{id}/phase`, `PATCH /machines/{id}/phase`, `PATCH
  /implementations/{id}/phase` accept `{status_id: UUID | null}` -
  `null` clears the override and reverts to inheriting.
- Every override write still goes through the shared `AuditRecorder` hook
  (action `plant.phase_changed` / `machine.phase_changed` /
  `implementation.phase_changed`), consistent with every other write in this
  phase.
- The frontend, not the backend, computes "does this deviate from its parent"
  and "what is the effective phase" - this keeps the backend simple (just
  store/return the raw nullable override) at the cost of requiring the full
  ancestor chain to already be loaded client-side to render correctly. Fine for
  the sidebar tree and project detail page, which already load the whole
  Plant > Machine > Implementation tree per project.
