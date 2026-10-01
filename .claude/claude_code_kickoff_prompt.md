# Claude Code Kickoff Prompt — EngineOps

## 1. Product context

EngineOps is a multiuser engineering operations platform for an industrial automation team.
It combines project planning and execution, configurable Kanban boards, a two-level Schedule,
material/piece tracking, project files, membership, administration, and an append-only project
timeline.

The current work model is authoritative:

```text
Project
├── Milestone
│   └── Task
│       └── Subtask
└── Task
    └── Subtask
```

Do not reintroduce Issue as an active product entity. Historical migrations and ADRs may use
that term because they describe superseded states.

## 2. Work-model invariants

- Projects own Milestones and Tasks.
- Milestones are optional organizational containers for top-level Tasks.
- A Task may exist without a Milestone.
- Tasks and Subtasks use the same entity and `tasks` table.
- `parent_task_id IS NULL` means Task; non-null means Subtask.
- Subtasks must have exactly one top-level Task parent in the same Project.
- Subtask → Subtask, self-parenting, cycles, and cross-project parenting are invalid.
- Only top-level Tasks store `milestone_id`; Subtasks inherit it logically from their parent.
- A Task with children cannot become a Subtask or be deleted.
- A Task cannot become `done` while any Subtask is incomplete.
- A completed parent cannot gain an incomplete Subtask or have one reopened beneath it.
- Milestone progress counts top-level Tasks only.
- Project Kanban and My Kanban display top-level Tasks only.
- Schedule supports exactly Task → Subtask; no recursive hierarchy.

The backend application service layer is authoritative for these rules. React checks are UX
safeguards. FastAPI routers translate HTTP and repositories persist; neither is the home of
business invariants.

## 3. Current product surfaces

- **Dashboard:** top-level Task metrics; never double-count Subtasks.
- **Milestones:** CRUD, progress, and top-level Task membership.
- **Tasks:** filtering, Task Detail, Subtask management, labels, comments, and history.
- **Kanban:** dynamic boards/columns mapped to `task_status`; cards are top-level Tasks.
- **Schedule:** Task/Subtask dates, direct-child rollup, ordering, and valid reparenting.
- **Material:** part numbers, pieces, conditions, locations, and measurements.
- **Files:** project-scoped file tree and content.
- **Timeline:** a project-filtered rendering of append-only `audit_log`.
- **Administration:** users and roles; authentication state is durable.

## 4. Technology and deployment

- Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2.
- PostgreSQL 16; normalized schema and migrations only, never manual production DDL.
- JWT authentication with passlib/bcrypt.
- React, TypeScript, Vite, Tailwind CSS, and `@dnd-kit`.
- MinIO for object storage.
- Docker Compose must preserve clone → `docker compose up -d` as the working local path.
- Python dependencies live in `api/pyproject.toml`; frontend dependencies use the committed
  package lockfile.

## 5. Architecture

Continue the repository's hexagonal separation:

```text
Domain entities and rules
        ↓
Application services / use cases
        ↓
Repository ports
        ↓
SQLAlchemy adapters
        ↓
FastAPI dependency wiring and routes
```

Domain and application modules must not import SQLAlchemy, FastAPI, or React. Repository
adapters perform persistence and efficient aggregates. API routes call services rather than
bypassing validation. The frontend consumes API contracts and does not reconstruct core
invariants from incomplete client state.

`audit_log` is written transactionally alongside mutations through the shared audit service.
Do not create a second timeline/feed source of truth.

## 6. Database and migration safety

Historical migrations are immutable. Add a new revision after the current head for every
schema change.

The durable authentication graph is:

```text
users ──< user_roles >── roles
```

Never delete or recreate these tables during a project-data reset. Preserve user IDs, emails,
password hashes, account status, roles, and assignments. Project-owned references to users may
be reset only when the relevant product migration explicitly permits project data loss.

Migration 0027 is the intentional boundary between the historical tracking schema and the
Task/Milestone model. See `docs/architecture/adr/0016-task-hierarchy.md` before changing Tasks,
Milestones, Kanban status mappings, or Schedule hierarchy.

## 7. Development workflow

- Preserve unrelated changes in the working tree.
- Keep modules focused; split files approaching roughly 400 lines.
- Public Python functions and methods need typed signatures.
- Use the repository's line length of 99.
- Add tests at the lowest useful layer and API/integration coverage for cross-layer behavior.
- Run focused checks while developing, then backend lint/tests and frontend tests/build.
- Review active code for obsolete terminology; historical migration and ADR matches are valid.

Backend verification:

```bash
cd api
ruff check .
black --check .
pytest
alembic upgrade head
```

Frontend verification:

```bash
cd web
npm run test -- --run
npm run build
```

## 8. Completion checklist

- [ ] Task/Milestone hierarchy and completion invariants remain centralized in services.
- [ ] Task lists, metrics, Kanban, and Milestone progress use top-level Tasks where required.
- [ ] Subtasks remain direct children only and never independent Project Kanban cards.
- [ ] Labels, comments, audit history, and Schedule work for Tasks and Subtasks.
- [ ] User/authentication data survives every migration direction.
- [ ] New schema changes have a new Alembic revision and, when architectural, an ADR.
- [ ] Backend checks pass.
- [ ] Frontend tests and production build pass.
- [ ] Current documentation describes Task, not the superseded Issue model.
