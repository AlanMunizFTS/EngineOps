# ADR 0015: Admin panel, deletable users, and local-part login

## Status

Accepted.

## Context

Three related requests: remove a leftover test user ("Verify Two"), let
users log in with just the part of their email before the `@` instead of
typing the full `@martinrea.com` address, and give an admin a panel to
create new user accounts.

The first request immediately hit a real blocker: `UserRepository` had no
`delete` method at all, and even adding one naively would have failed -
`projects.created_by`, `issues.created_by`, `issue_comments.author_id`, and
`audit_log.actor_id` were all `NO ACTION` (blocking) foreign keys to
`users`. "Verify Two" is the creator of record for the "Endforms Standard"
project - the one this session had just spent hours populating with 121
issues - so a naive `DELETE FROM users` would have failed outright (blocked
by `projects.created_by`), not cascaded destructively. Still, any admin
"delete a user" feature needs to work for *any* user with real history, not
just ones with none.

There was also no admin concept anywhere: `User.roles` (a global
`roles`/`user_roles` many-to-many) already existed in the schema but wasn't
read by any authorization check - `UserResponse.roles` was returned to the
frontend and simply never acted on.

## Decisions

**User-referencing FKs that were `NO ACTION` become `ON DELETE SET NULL`**
(migration 0022): `projects.created_by`, `issues.created_by`,
`issue_comments.author_id`, `audit_log.actor_id`. This extends a pattern
already established for `file_tree_nodes.created_by` and
`issues.assignee_id` - deleting the user who made something shouldn't be
blocked by, or cascade-delete, the thing they made. A project/issue/comment
outlives its creator; an audit log entry is a historical record independent
of whether the actor still exists. The corresponding domain entities
(`Project.created_by`, `Issue.created_by`, `IssueComment.author_id`,
`AuditLogEntry.actor_id`) and response schemas all became `UUID | None` to
match. `create()`/`record()` port methods that *write* these fields stay
non-optional - a new project/issue/comment/audit-entry is always created by
a real, currently-authenticated user; only the *stored, later-read* value
can become `None` after that user is gone.

**Admin authorization reuses the existing `roles` table rather than adding
an `is_admin` boolean.** A `get_current_admin_user` dependency
(`api/deps.py`) checks `"admin" in [r.name for r in user.roles]`, 403s
otherwise. This is the first thing in the codebase that actually reads
`User.roles` for a decision - the table/relationship/response field were
already fully wired, just unused. Migration 0023 seeds one `admin` `Role`
row and grants it to the known dev bootstrap account
(`localfts@martinrea.com`) if that email exists; a real deployment without
that seed email is a no-op, and the standard first-admin bootstrap problem
applies (an operator grants the first admin via direct DB access, same as
any system's first superuser).

**New `/admin` router**: `GET /admin/users` (list), `POST /admin/users`
(create, with an `is_admin` flag), `DELETE /admin/users/{id}` (delete) -
all behind `get_current_admin_user`. Deleting yourself is rejected (400) as
a cheap footgun guard; nothing stops deleting the *last* admin otherwise,
kept simple per this repo's established pre-production precedent (ADR
0005, 0006, 0009, 0010, 0013) rather than adding quorum-checking logic for
a scenario that's easy to recover from via direct DB access anyway.

**Login accepts a bare local-part.** `LoginRequest.email` changed from
Pydantic's `EmailStr` (which would reject "jdoe" outright, no `@`) to a
plain `str`. `core/security.py::normalize_login_identifier` appends
`@martinrea.com` only when the input contains no `@` - an input that's
already a full email (including non-martinrea test/seed accounts) is used
unchanged. This is a login-time convenience only: `/auth/register` and the
new admin create-user endpoint both still require a real, fully-qualified
email (`EmailStr`) - only the *login* identifier gets the shorthand,
because that's the only place typing the full domain repeatedly is pure
friction with no data-integrity value.

**Frontend**: `LoginPage`'s email field is now a plain text input
("Username or email") instead of `type="email"`, since a bare local-part
isn't a valid HTML5 email value and the browser would block submission.
`AdminUsersPage.tsx` (list + create + delete) is gated both by hiding the
nav entry (`TopBar`, only shown when `user.roles.includes("admin")`) and by
the page itself checking the same condition - the actual enforcement is
still server-side (403), the frontend checks are just UX, not security.

## Consequences

- Any future "delete a user" flow (this admin panel or otherwise) now
  works uniformly regardless of what that user created - no more per-table
  surprises about which FK blocks the delete.
- `created_by`/`author_id`/`actor_id` being `null` is now a real, visible
  case any UI reading those fields should tolerate (e.g., "created by
  —" instead of assuming a resolvable user). Nothing currently renders
  these fields directly enough for this to matter today, but it's a
  standing contract now, not a hypothetical.
- The `admin` role is global, not project-scoped - unrelated to
  `ProjectRole` (owner/contributor/viewer), which still governs
  per-project permissions. An admin can manage user accounts platform-wide
  but that says nothing about their access within any given project.
- Deleting a user is irreversible in this UI (no soft-delete), consistent
  with this repo's established stance on destructive operations
  pre-production.
