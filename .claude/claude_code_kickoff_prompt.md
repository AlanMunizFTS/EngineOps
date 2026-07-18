# Claude Code Kickoff Prompt — Engineering Ops Platform

> Paste this entire prompt into Claude Code inside VS Code, in the empty project folder you want to become the Git repo root.

---

## 1. Context & Role

You are bootstrapping a **multiuser, GitHub-inspired engineering operations platform** for an industrial automation team (controls/vision engineers). The platform manages: projects, machines, implementations (deployed instances of a project on a machine), a component/BOM catalog, stock/inventory, quoting, standardized versioned documents (SOW, SOR, BOM format, project charters, buyoffs), versioned technical deliverables (PLC/HMI backups, tag lists, IP registries, CAD files, troubleshooting guides, training material, operation manuals, code flow diagrams), and GitHub-equivalent project tracking: **issues, kanban boards, milestones, labels, and a project timeline/activity feed**.

Every entity must be traceable: who changed what, when, and what it looked like before. Treat this as a real production system, not a prototype — production-style code, migrations, tests, and Docker from day one.

**Deployment requirement (non-negotiable):** the entire stack must come up with a single command after cloning:

```bash
git clone <repo-url>
cd <repo-folder>
docker compose up -d
```

No manual `.env` editing required to get a working local instance (ship a `.env.example` that's copied automatically or defaulted in `docker-compose.yml`), no separate realm/config bootstrapping steps. If a service normally needs manual setup (e.g., an identity provider), **defer it and use simple built-in JWT auth for now** — auth complexity that blocks the "clone → up → done" promise gets pushed to a later phase.

---

## 2. Tech Stack (fixed — do not deviate without asking)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic for migrations, Pydantic v2 for schemas
- **Database:** PostgreSQL 16, fully normalized to 3NF, all schema changes via Alembic migrations (never manual SQL against a running DB)
- **Auth (Phase 0):** built-in JWT (passlib/bcrypt for hashing) — no external IdP yet
- **File/object storage:** MinIO (S3-compatible), containerized, for CAD/PLC/HMI binaries
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Drag-and-drop kanban:** `@dnd-kit` (lightweight, no extra backend dependency) for the board UI
- **Containerization:** Docker + Docker Compose (single `docker-compose.yml` at repo root orchestrating: `api`, `db`, `minio`, `web`, plus an `api-migrate` init step that runs Alembic migrations before `api` starts)
- **Code style:** strict PEP 8 (`ruff` + `black` configured, pre-commit hook), fully modular — no monolithic files, one responsibility per module/router/service

---

## 3. Git Workflow (mandatory for every phase)

- `main` is always deployable — never commit directly to it.
- One branch per phase, named `phase-N-<short-scope>` (e.g. `phase-0-foundations`).
- Within a phase branch, commit **incrementally per logical unit of work** (e.g. "add Project model + migration", "add Project CRUD router", "add Project schema tests") — never one giant commit per phase.
- Commit message format: `[phase-N] <imperative summary>` (e.g. `[phase-0] add docker-compose skeleton with api/db/minio`).
- At the end of each phase: push the branch, open a PR into `main` with a description listing the phase's scope and what was completed, then merge (simulate this even if working solo — the PR description is the audit trail).
- Tag `main` after each phase merge: `v0.<phase-number>.0`.

Do not start Phase N+1 until Phase N is merged and the "Definition of Done" below is satisfied — confirm with me before moving on.

---

## 4. Data Model to Implement (reference — build incrementally per phase, not all at once)

```
users, roles, project_members
projects
machines(project_id, ...)
implementations(machine_id, project_id, label, status, superseded_by, ...)

-- GitHub-equivalent project tracking
labels(project_id, name, color)
milestones(project_id, title, description, due_date, status)
issues(
    project_id, implementation_id NULL, title, description,
    status,        -- backlog | todo | in_progress | in_review | done  (= kanban columns)
    priority, issue_type,   -- bug | task | improvement | incident
    milestone_id NULL, assignee_id, created_by, created_at, closed_at
)
issue_labels(issue_id, label_id)
issue_comments(issue_id, author_id, body, created_at, edited_at)
kanban_boards(project_id, name)
kanban_columns(board_id, name, order_index, maps_to_status)  -- customizable per project, defaults seeded from issue.status enum

components, project_bom
stock_locations, stock_levels, stock_movements
quotes, quote_line_items

-- Procurement: quote -> PO -> shipment -> invoice, all traceable back to the project
purchase_orders(
    project_id, quote_id NULL, supplier, po_number, status,
    -- status: draft | submitted | confirmed | partially_received | received | cancelled
    created_by, created_at
)
po_line_items(po_id, component_id, quantity, unit_cost, expected_delivery_date)

shipments(
    po_id, carrier, tracking_number, status,
    -- status: pending | in_transit | delivered | delayed | exception
    shipped_at, estimated_arrival, received_at
)
shipment_items(shipment_id, po_line_item_id, quantity_shipped, quantity_received)

invoices(
    po_id, supplier, invoice_number, file_path,   -- file stored in MinIO like any other deliverable
    amount, currency, status,
    -- status: received | approved | disputed | paid
    issued_date, due_date, paid_date
)

document_templates(doc_type, template_version, ...)
project_documents(project_id, implementation_id, doc_type, template_id, ...)
project_document_versions(project_document_id, version_number, status, approved_by, ...)
deliverables(project_id, machine_id, implementation_id, type, ...)
deliverable_versions(deliverable_id, version_number, file_path, checksum, ...)

-- Timeline / traceability (append-only, never updated/deleted)
audit_log(
    project_id,               -- denormalized on every row for fast per-project timeline queries
    actor_id, entity_type, entity_id, action, diff_json, occurred_at
)

network_devices(project_id, ip_address, hostname, device_type, vlan, ...)
```

`audit_log` must be written transactionally alongside every create/update/delete across **all** modules, including issue status changes, comments, kanban card moves, PO placements, shipment status updates, and invoice receipt/approval/payment — implement this as a reusable service-layer hook, not copy-pasted logging in every router. The project **timeline view is just a filtered, human-readable rendering of `audit_log` where `project_id = X`, ordered by `occurred_at`** — don't build a separate feed table; that would just be a second source of truth to keep in sync.

---

## 5. Phase-by-Phase Scope

### Phase 0 — Foundations (`phase-0-foundations`)
- Repo scaffold: `/api` (FastAPI app), `/web` (React app), `docker-compose.yml`, `.env.example`, `README.md` with the one-command deploy instructions
- PostgreSQL container + Alembic wired up, `api-migrate` init container running migrations on `docker compose up`
- `users`, `roles`, `project_members` tables + JWT login/register endpoints
- Basic React shell with login page hitting the API
- CI: GitHub Actions workflow running `ruff`, `black --check`, and backend tests on every push
**Definition of Done:** `git clone` + `docker compose up -d` yields a working login screen against a real Postgres DB, with a green CI badge.

### Phase 1 — Projects, Machines, Implementations (`phase-1-project-hierarchy`)
- Full CRUD for `projects`, `machines`, `implementations`
- Project detail view in React showing its machines and each machine's implementations
- `audit_log` hook implemented (with `project_id` on every row) and firing on all writes in this phase
**DoD:** can create a project, attach 2+ machines, attach 2+ implementations to one machine, and see the audit trail for each action.

### Phase 2 — Issues, Kanban & Timeline (`phase-2-issues-kanban-timeline`)
- `labels`, `milestones`, `issues`, `issue_labels`, `issue_comments`
- Issue list view: filter/search by status, assignee, label, milestone — this is the "Issues tab" equivalent
- Kanban board view (`kanban_boards`/`kanban_columns`): drag-and-drop cards between columns, each move updates `issues.status` and fires an `audit_log` event
- Milestone progress view: % of issues closed per milestone (GitHub's milestone progress bar equivalent)
- Timeline/activity feed component: chronological render of `audit_log` scoped to a project — issue created, status changed, comment added, deliverable uploaded, document approved, etc. all show up in one unified feed
- Comment threads on issues with basic @mention parsing (stored as plain text references for now — no notification delivery yet, that's a later polish item)
**DoD:** create an issue, move it across kanban columns via drag-and-drop, add a comment, and confirm all three actions appear correctly ordered in the project timeline.

### Phase 3 — Deliverables & Versioning (`phase-3-deliverables`)
- `deliverables` + `deliverable_versions`, MinIO integration for file storage, checksum computation on upload
- Upload UI supporting all deliverable types (PLC/HMI backups, tag lists, IP lists, CAD, docs, manuals, guides, diagrams)
- Version history view per deliverable (who/when/checksum/notes), download by version
- Deliverable uploads/version changes also emit `audit_log` events, appearing in the Phase 2 timeline
**DoD:** upload two versions of a PLC backup to the same deliverable, confirm checksum differs, confirm both versions downloadable independently, confirm both appear in the project timeline.

### Phase 4 — Standard Document Templates (`phase-4-document-templates`)
- `document_templates`, `project_documents`, `project_document_versions`
- Seed default templates for SOW, SOR, BOM format, project charter, buyoff
- Buyoff approval workflow: `status` field (draft/submitted/approved/rejected) + `approved_by`/`approved_at`
- UI to generate a project document from the active template version and track its own version history independently of template updates
**DoD:** create a buyoff from the current template, submit it, approve it, then update the template to a new version and confirm the already-created buyoff still references its original template version.

### Phase 5 — BOM, Stock, Quoting & Procurement Tracking (`phase-5-bom-stock-quoting-procurement`)
- `components`, `project_bom`, `stock_locations`, `stock_levels`, `stock_movements`
- `quotes`, `quote_line_items` with live cost pull from components
- Low-stock indicator on components reserved by active projects
- **Purchase orders:** `purchase_orders` + `po_line_items`, optionally generated directly from an approved quote (pre-filling supplier/line items/costs), or created standalone
- **Shipment tracking:** `shipments` + `shipment_items`, linked to a PO; status transitions (pending → in_transit → delivered/delayed/exception) are manually updated for now — a carrier-API integration (UPS/FedEx/DHL tracking webhook) is a good Phase 8+ candidate once the core flow is proven, don't build that integration yet
- **Invoices:** `invoices`, file stored in MinIO exactly like a deliverable (reuse the same upload/versioning component, don't build a second file-upload path), linked to a PO for reconciliation (invoice amount vs. PO line item totals)
- **Receiving flow:** marking a `shipment_item` as received automatically creates the corresponding `stock_movements` row (increasing `quantity_on_hand`) — this is the one place where one user action should cascade into a second table write; do it in a single transaction, not two separate API calls
- **Timeline linkage:** PO placement, each shipment status change, and invoice status change (received/approved/disputed/paid) all emit `audit_log` events, so a project's timeline reads as a real procurement story end-to-end: *quote approved → PO placed → shipped → delayed → delivered → stock received → invoice received → invoice paid*
- Project view: a "Procurement" tab showing open POs, in-transit shipments, and pending/overdue invoices for that project — the same underlying data the timeline renders, just filtered to a status-oriented view instead of chronological
**DoD:** approve a quote, generate a PO from it, create a shipment against the PO, mark it delivered (confirm stock levels increment automatically), upload an invoice and mark it paid — confirm all six of those events appear correctly ordered in the project timeline.

### Phase 6 — Network/IP Registry (`phase-6-network-registry`)
- `network_devices` CRUD scoped per project/implementation
- Conflict detection: warn if an IP is reused across active implementations in the same VLAN
**DoD:** register devices for two implementations, trigger and confirm the IP-conflict warning works.

### Phase 7 — Polish & Multi-user Hardening
- Role-based permissions enforced at the API layer (not just hidden UI elements)
- Pagination, search, and filtering across all list views (issues, deliverables, documents)
- Notification delivery for @mentions and assignment (in-app, email deferred)
- Dashboard: active projects, open issues by priority, pending buyoffs, low stock, recent timeline events across all projects the user is a member of
**DoD:** two different user roles see appropriately restricted views and cannot perform actions outside their permissions via direct API calls.

---

## 6. Instructions to Claude Code

- Confirm the Phase 0 branch and scaffold before writing any application code.
- After each phase's DoD is met, stop, summarize what was built and how to verify the DoD manually, and wait for confirmation before opening the PR and starting the next phase.
- If any requirement here is ambiguous or you need a product decision (e.g., an exact field, a UI layout choice), ask — don't assume silently for anything that affects the data model.
- Never commit `.env` files with real secrets; only `.env.example` with placeholder values.
