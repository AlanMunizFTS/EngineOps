# EngineOps

Multiuser, GitHub-inspired engineering operations platform for an industrial automation team:
projects, machines, implementations, BOM/stock/quoting/procurement, issues/kanban,
versioned documents and deliverables, and a full project audit trail/timeline.

Being built incrementally by phase — see `.claude/claude_code_kickoff_prompt.md` for the full
spec. This is **Phase 1 — Projects, Machines, Implementations**.

## Quickstart

```bash
git clone <repo-url>
cd EngineOps
docker compose up -d
```

That's it — no manual `.env` editing required. `docker-compose.yml` defaults every variable
(see `.env.example` for the values), Postgres and MinIO come up, `api-migrate` runs Alembic migrations, then the API and web app start.

- API: http://localhost:8000 (docs at `/docs`)
- Web: http://localhost:5173
- MinIO console: http://localhost:9001

To use custom values (e.g. a real JWT secret), copy `.env.example` to `.env` and edit it —
Docker Compose picks up `.env` automatically.

### First admin user

`POST /auth/register` and `POST /auth/users` require an authenticated user and create accounts
with zero roles - there's no "first user becomes admin" magic. Bootstrap the first admin explicitly:

```bash
docker compose exec api python utils/create_admin.py --email admin@example.com --password "change-me"
```

Idempotent - re-running it just confirms the user/role already exist. Role-based
**enforcement** isn't wired up until Phase 7, so this doesn't unlock anything today beyond
having a user flagged `admin` in the database ahead of that.

## Phase 0 scope

- `users`, `roles`, `user_roles` tables (Alembic migration, seeded with `admin`/`engineer`/`viewer`)
- JWT register/login (`POST /auth/register`, `POST /auth/login`, `GET /auth/me`)
- React login page wired to the real API
- CI: `ruff`, `black --check`, `pytest` on every push

`project_members` (Phase 0 kickoff spec) is deferred to Phase 1 alongside `projects`, since it
needs a real foreign key to a table that doesn't exist yet — see the Phase 0 PR description.

## Phase 1 scope

- `projects`, `project_members` (project-scoped `owner`/`contributor`/`viewer` roles, distinct
  from the global roles in `user_roles`)
- Project progress tracked as multiple independent per-area tracks instead of a single
  `projects.status` field — `area_types`/`area_statuses` (seeded catalog: Scope & Charter,
  Procurement, Import/Export, Electrical, Mechanical, Vision) and `project_areas` (one row per
  project × area type, each with its own status). See
  `docs/architecture/adr/0001-project-area-status-tracking.md` for why.
- `machines`, `implementations` (`implementations.status`: `planned`/`active`/`superseded`/
  `decommissioned`, with `superseded_by` linking to the replacing implementation)
- `audit_log`, written transactionally alongside every write in this phase via a shared
  `AuditRecorder` hook (not copy-pasted logging per router). `GET /projects/{id}/timeline` is
  just this table filtered and ordered — no second feed table.
- React: projects list + create-project form, project detail page (area status tiles, machines
  with their implementations, timeline feed)

Creating a project auto-creates the creator as `owner` and one `project_area` per seeded area
type, all in one transaction. Role-based **enforcement** of `project_members` (who can actually
write to a project) is deferred to Phase 7 per the kickoff spec — Phase 1 only establishes the
membership data.

## Moving to another computer

The project only needs Docker Desktop on the destination machine — `web/node_modules` and
`api/.venv` are never copied into the images (selective `COPY` in `api/Dockerfile`,
`web/.dockerignore` excludes `node_modules`) and get rebuilt fresh from `pyproject.toml` /
`package.json` on first `docker compose up --build`. Skip both folders (plus `__pycache__`,
`.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `web/dist`) when copying — the whole source tree
without them is a couple MB.

```powershell
docker compose up -d --build
docker compose exec api python utils/create_admin.py --email admin@example.com --password "change-me"
```

**The database is not part of the folder.** Postgres data lives in a Docker-managed named
volume (`db_data`), not inside the repo tree, so copying/zipping the project never carries
users/projects/issues with it — `docker compose up --build` alone gives you an empty,
freshly-migrated schema. To bring existing data along, run on the **source** machine (stack must be up):

```powershell
.\scripts\export-data.ps1
```

This writes `EngineOps-data-backup.sql` to the repo root (git-ignored — it contains real
password hashes, never commit it). It's a data-only dump (schema comes from Alembic) that
also re-derives `user_roles` grants by role name rather than copying `roles.id` directly,
since that ID is a random UUID the seed migrations regenerate on every fresh install and
would never match the destination's. Copy that `.sql` file alongside the project, then on the
destination machine, **after** `docker compose up -d --build` has finished (so the
schema/migrations already exist):

```powershell
.\scripts\import-data.ps1
```

If `docker compose up` fails to bind a port (commonly `8000`), Windows may have it stuck in a
Hyper-V/WSL2 reserved TCP range:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

If so, copy `.env.example` to `.env` (or edit the existing `.env`) and set `API_PORT`/`WEB_PORT`
to something outside the excluded range — Docker Compose picks up `.env` automatically, no
other changes needed.

## Local development (without Docker)

```bash
cd api
pip install -e ".[dev]"
alembic upgrade head
uvicorn ops_platform.main:app --reload
```

```bash
cd web
npm install
npm run dev
```

## Architecture

- Hexagonal (ports & adapters): `api/src/ops_platform/domain/ports/` defines interfaces;
  `api/src/ops_platform/adapters/` implements them for Postgres/SQLAlchemy. Domain and API
  layers never import SQLAlchemy directly.
- PostgreSQL 16, 3NF, all schema changes via Alembic — no manual SQL against a live DB.
