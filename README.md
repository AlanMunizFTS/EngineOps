# EngineOps

Multiuser engineering operations platform for an industrial automation team. EngineOps brings
project planning, execution, material tracking, files, and audit history into one workspace.

Work follows one strict hierarchy:

```text
Project
├── Milestone
│   └── Task
│       └── Subtask
└── Task
    └── Subtask
```

Milestones organize top-level Tasks. Tasks may exist without a Milestone, while Subtasks always
belong directly to one Task; deeper nesting is not supported. Project Kanban shows top-level
Tasks, Task Detail owns Subtask execution, and Schedule plans the same two-level work model.

## Quickstart

```bash
git clone <repo-url>
cd EngineOps
docker compose up -d
```

No manual `.env` editing is required. `docker-compose.yml` supplies development defaults,
PostgreSQL and MinIO start, `api-migrate` upgrades the schema, and then the API and web app run.

- API: <http://localhost:8000> (`/docs` for OpenAPI)
- Web: <http://localhost:5173>
- MinIO console: <http://localhost:9001>

For custom values, copy `.env.example` to `.env` and edit it. Never commit real secrets.

### First admin user

Bootstrap the first admin explicitly:

```bash
docker compose exec api python utils/create_admin.py \
  --email admin@example.com --password "change-me"
```

The command is idempotent; re-running it confirms that the user and role already exist.

## Product model

- **Projects** are the root workspace and retain membership, files, Schedule, Material, and
  settings.
- **Milestones** group top-level Tasks and calculate progress from those Tasks only.
- **Tasks** are executable top-level work. Their status drives Project and My Kanban.
- **Subtasks** share the Task entity but are direct children of a Task. They do not appear as
  independent Kanban cards and cannot contain another Subtask.
- **Kanban** uses configurable boards and columns mapped to Task statuses.
- **Schedule** renders Task → Subtask planning, including dates and direct-child rollups.
- **Material** tracks project part numbers, pieces, conditions, locations, and measurements.
- **Audit history** is append-only and exposed as the project timeline.

The backend follows hexagonal architecture: business invariants belong in application
services, persistence in SQLAlchemy adapters, and HTTP translation in FastAPI routes. See
[`docs/architecture/adr/0016-task-hierarchy.md`](docs/architecture/adr/0016-task-hierarchy.md)
for the Task/Milestone decision and migration boundary.

## Local development

Backend:

```bash
cd api
pip install -e ".[dev]"
alembic upgrade head
uvicorn ops_platform.main:app --reload
```

Frontend:

```bash
cd web
npm install
npm run dev
```

Useful verification commands:

```bash
cd api
ruff check .
black --check .
pytest

cd ../web
npm run test -- --run
npm run build
```

## Moving data to another computer

Application dependencies are rebuilt from `api/pyproject.toml` and `web/package-lock.json`.
Do not copy `.venv`, `node_modules`, caches, or `web/dist`.

PostgreSQL data lives in Docker's `db_data` volume and is not contained in the repository.
To export data from a running source stack:

```powershell
.\scripts\export-data.ps1
```

Copy the generated `EngineOps-data-backup.sql` separately; it contains password hashes and is
git-ignored. On the destination, start and migrate the stack before importing:

```powershell
docker compose up -d --build
.\scripts\import-data.ps1
```

Migration 0027 intentionally resets project-owned data when moving from the historical Issue
model to Task/Milestone. It preserves `users`, `roles`, `user_roles`, password hashes, account
status, and role assignments. A pre-0027 full data export is therefore not a mechanism for
restoring old Issue/project data into the new model.

If a local port is reserved by Windows/Hyper-V, inspect reserved ranges and override
`API_PORT`, `WEB_PORT`, or other host ports in `.env`:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

## Architecture and schema rules

- Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL 16.
- React, TypeScript, Vite, Tailwind CSS, and `@dnd-kit`.
- Domain and application layers do not import SQLAlchemy or FastAPI.
- All schema changes use new Alembic revisions; historical migrations remain unchanged.
- Task hierarchy and completion invariants are enforced by the backend service layer. React
  checks are user-experience safeguards, not the authority.
- `users`, `roles`, and `user_roles` form the durable authentication boundary during project
  tracking resets.
