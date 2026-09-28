"""seed the "admin" role and grant it to the bootstrap dev admin account

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-23

Per docs/architecture/adr/0015-admin-panel-and-deletable-users.md: the
`roles`/`user_roles` tables already existed (unused by any authorization
check until now). This seeds a single "admin" role row and, if the known
dev bootstrap account (localfts@martinrea.com) exists, grants it - so there
is at least one admin able to use the new admin panel without needing
direct DB access. A deployment without that email is a no-op here; an
operator grants the first admin by inserting into `user_roles` directly
until the panel itself can promote a user (chicken-and-egg for the very
first admin, same as any first-admin bootstrap problem).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BOOTSTRAP_ADMIN_EMAIL = "localfts@martinrea.com"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO roles (id, name, description) "
            "VALUES (gen_random_uuid(), 'admin', 'Full administrative access') "
            "ON CONFLICT (name) DO NOTHING"
        )
    )
    conn.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT u.id, r.id FROM users u, roles r "
            "WHERE u.email = :email AND r.name = 'admin' "
            "ON CONFLICT DO NOTHING"
        ),
        {"email": _BOOTSTRAP_ADMIN_EMAIL},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM user_roles WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')"
        )
    )
    conn.execute(sa.text("DELETE FROM roles WHERE name = 'admin'"))
