# CLAUDE.md

## 0. EngineOps product model

For this repository, the active planning hierarchy is strictly:

```text
Project → optional Milestone → Task → optional direct Subtasks
```

Task and Subtask are the same domain entity; `parent_task_id` alone determines hierarchy.
Never allow Subtask nesting, cross-project parents, self-parenting, or cycles. Only top-level
Tasks own `milestone_id` and appear on Project/My Kanban. Schedule supports one child level.
Task completion and deletion invariants belong in application services, not routes, adapters,
or React. `docs/architecture/adr/0016-task-hierarchy.md` is authoritative.

Issue is historical terminology only. It may remain in pre-0027 Alembic revisions and
superseded ADRs, but must not be used by active application code or current product guidance.

During any destructive project-data migration, preserve `users`, `roles`, `user_roles`,
password hashes, account status, and role assignments. Never rewrite historical migrations.

Persistent instructions for Claude Code on Sebastian's projects (Controls/Vision Engineer,
Martinrea International, FTS/Factory of the Future team — AI-powered visual inspection,
edge AI on NVIDIA Jetson, industrial database architecture, PLC/HMI integration,
multi-plant standardization).

> Project-type folder templates and future-platform mapping have been split into
> `.claude/rules/project-templates.md` and `.claude/rules/platform-mapping.md` — they load
> only when Claude works on those topics, keeping this core file lean.

## 1. Language & Communication

- Always respond in English — explanations, comments, and code, regardless of the language
  the request is written in.
- Professional, concise, technical tone. No unnecessary verbosity unless deeper explanation
  is explicitly requested.
- Structured responses: sections, bullets, steps. Conceptual clarity first, implementation
  details second.
- Assume technical competence — don't over-confirm obvious things. If ambiguous, ask a
  targeted clarifying question rather than guessing.
- If multiple approaches exist, present the top 2–3 with pros/cons rather than picking one
  silently.

## 2. Code Style — enforced by tooling, not memory

| Tool | Purpose |
|---|---|
| `ruff` | linting + import sorting (PEP 8: E/W, F, I, N, UP, B rules) |
| `black` | formatting |
| `mypy` | static typing (`strict = true` on shared libs; relaxed on services during prototyping, documented per-service) |
| `pre-commit` | runs all of the above before every commit |

- Line length: 99 (modern accepted convention; adjust in `pyproject.toml` if the team wants
  88 or the PEP 8 nominal 79 — must be explicit, never ambiguous).
- Every public function/method has type-annotated signatures.
- PEP 8 compliance is mandatory on **every surface** — web portal, VS Code, CI — same
  `pyproject.toml` config everywhere, not surface-specific rules.

## 3. Modularity — hard limits

- No monolithic scripts. No file over ~400 lines — if a module grows past that, split the
  bounded context.
- No function over ~50 lines / one clear responsibility.
- Config (IPs, PLC tags, thresholds, model paths) lives in `config/*.yaml` or environment
  variables — never hardcoded in source (12-Factor: config in the environment).

## 4. Communication efficiency (cycle-time-critical code)

Given real-time industrial/PLC/vision-cycle work, every millisecond in a cycle matters:

- Avoid unnecessary allocations inside loops — pre-allocate buffers/arrays instead of
  appending in hot paths.
- Minimize blocking calls in cycle-critical paths — flag where non-blocking I/O (e.g.
  async socket reads for PLC polling) would reduce jitter.
- Call out Big-O behavior when it matters; flag when a "clean" abstraction would cost
  latency in a tight loop so the tradeoff is made explicitly, not inherited silently.
- Document timing assumptions and protocol quirks (Sysmac tag polling, Modbus/EtherNet-IP
  timing) in docstrings/comments — not just what the code does, but why the timing matters.

## 5. Database — PostgreSQL by default, normalized

- PostgreSQL is the default engine for any new database, unless a specific constraint
  (edge deployment, existing plant stack) forces otherwise — call this out explicitly if so.
- Schemas designed to 2NF/3NF by default. Deliberate denormalization (e.g. a read-optimized
  reporting/aggregation table) requires an explicit ADR (§9) — never introduced silently.
- Example 3NF pattern for traceability-style schemas: lookup tables for repeated categorical
  values instead of repeating strings — e.g. `defect_types` (id, name, description) referenced
  by FK from `defects`, rather than a `defect_type` string column repeated per row.
- Agent long-term memory / RAG context uses `pgvector` on the same Postgres instance rather
  than a second database engine, unless scale forces otherwise (ADR if so).
- All schema changes go through Alembic migrations — no manual schema edits against a live DB.
- Time-series-heavy data (digital twin telemetry) uses TimescaleDB on top of Postgres, not a
  separate system.

## 6. Architecture — Ports & Adapters (Hexagonal) + DDD bounded contexts

**Mandatory rule:** domain/business logic never imports a hardware driver, LLM SDK, message
broker client, or DB driver directly. It depends on a `Port` (abstract interface); an
`Adapter` implements that Port for a specific technology.

```
services/ingestion/
├── ports/
│   └── camera_source.py       # ABC: CameraSource.read_frame() -> Frame
└── adapters/
    ├── gige_camera_adapter.py  # real implementation
    └── mock_camera_adapter.py  # test/CI implementation
```

Why: this is the pattern that already let Sebastian swap Gocator → in-house profilometer,
and Omron → any future PLC vendor, without touching inspection logic.

**Bounded contexts (DDD):** each folder under `services/` owns its own model of its core
concepts and does not reach into another service's internals. Cross-context communication
happens only through `libs/schemas/` (versioned event/API contracts) or `event_bus/`.
Anti-pattern to reject: one service importing another service's internal model class
directly — if they need to share a concept, that concept becomes a schema in `libs/schemas/`.

## 7. Packaging

- PyPA `src` layout: installable code under `src/<package_name>/`, never flat at repo root.
- `pyproject.toml` is the only manifest (PEP 518/621) — no `setup.py`, no hand-maintained
  `requirements.txt` as source of truth.

## 8. Diagrams — C4 Model

- Every service has at minimum a C4 **Container** diagram in `docs/architecture/diagrams/`.
- System-level **Context** diagrams live at the repo root of that folder.
- Component/Code-level diagrams are optional — only where onboarding friction justifies the
  maintenance cost.

## 9. Architecture Decision Records (ADRs)

Any decision that's expensive to reverse gets a numbered ADR in `docs/architecture/adr/`
(Status / Context / Decision / Consequences format). Triggers: message broker choice,
schema denormalization, LLM provider lock-in, sync-vs-async service boundaries, edge-vs-cloud
placement of a workload.

## 10. Agent-specific rules (MCP + 12-Factor Agents)

- All agent tools registered through an MCP-compatible tool registry (name, description,
  typed JSON-schema input, handler) — no bespoke per-agent tool-calling convention.
- Agent prompts versioned as code, reviewed via normal PR process — never edited live in a
  dashboard without a corresponding commit.
- Agent state (conversation history, working memory, tool call log) is explicit and
  inspectable — never hidden inside an opaque SDK object that can't be logged or replayed.
- Every agent action affecting a physical process (PLC write, AMR dispatch, work order
  creation) passes through an explicit human-in-the-loop checkpoint state in the
  orchestrator, until that agent has an approved autonomy tier.

## 11. Standards this is grounded in (cite these, don't reinvent)

| Layer | Standard |
|---|---|
| OT/IT & digital twin layering | ISA-95 (Purdue Model), RAMI 4.0 |
| Software structure | Hexagonal Architecture (Cockburn), Domain-Driven Design |
| Packaging | PyPA `src` layout, PEP 518/621 |
| Agent tool interface | Model Context Protocol (MCP) |
| Diagramming | C4 Model (Simon Brown) |
| Ops conventions | 12-Factor App / 12-Factor Agents |
| Edge vision reference | NVIDIA Metropolis / Isaac (Jetson-specific) |

ISA-95/RAMI 4.0 give the architecture legitimacy with manufacturing-side stakeholders;
hexagonal/DDD language justifies the software structure; MCP is cited because it's an actual
open standard rather than a proprietary framework choice — this combination matters given the
P5/P6-level framing of the Manufacturing AI Solutions Architect role proposal.

## 12. Generic monorepo template (for new multi-service platforms)

```
platform_name/
├── pyproject.toml
├── docs/architecture/{adr/, diagrams/}
├── libs/{schemas/, telemetry/, auth/, db/}      # shared contracts across services
├── event_bus/topics/                             # topic/schema registry (Kafka/NATS/MQTT)
├── services/
│   ├── ingestion/{ports/, adapters/}             # OT/IT data plane
│   ├── digital_twin/                              # simulation/prediction engine
│   ├── agents/{core/, troubleshooting/, engineering/, quality/, maintenance/, controls/}
│   ├── orchestrator/                              # multi-agent coordination, debate logic
│   ├── logistics/                                 # AMR fleet mgmt, task allocation
│   └── api_gateway/
├── infra/{docker/, k8s/, terraform/}              # add k8s/terraform only once services split
└── tests/{unit/, integration/}
```

Start monolithic (single process, imported modules); the ports & adapters boundary means
extracting a service into its own container later is a deployment change, not a rewrite.

## 13. Project-Type Templates & Future Platform Mapping

Moved to `.claude/rules/` so they load only when relevant instead of consuming context
every session:

- `.claude/rules/project-templates.md` — per-domain folder structures (Python vision
  inspection, FPGA/embedded, Omron/ST, Jetson CV pipelines)
- `.claude/rules/platform-mapping.md` — **not yet created.** Intended to document how the
  generic monorepo template (§12) maps to TraceNet, the Digital Twin, the Autonomous Factory,
  Smart Warehousing, and the Multi-Agent Engineering Platform once those mappings are defined.

## 14. Review checklist (apply to every PR)

- [ ] No domain logic imports a concrete adapter directly (§6)
- [ ] No cross-service import outside `libs/` or `event_bus/` (§6)
- [ ] New/changed schema is 3NF or has an ADR justifying the exception (§5, §9)
- [ ] New event/API contract added to `libs/schemas/`, versioned (§6)
- [ ] Config values are not hardcoded (§3)
- [ ] Type hints present; `mypy` passes (§2)
- [ ] Tests added under `tests/unit/` (mocked adapters); `tests/integration/` only with
      simulated-hardware equivalence

---

*Project-type templates and future-platform mapping live in `.claude/rules/` — Claude Code
loads them only when relevant instead of every session.*
