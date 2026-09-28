# ADR 0008: SCOPE.md replaces the README card; file nodes carry editable content

## Status

Accepted. Extends [ADR 0007](0007-project-file-tree.md).

## Context

Every project needs a scope document, and the Dashboard tab already had a
GitHub-style "README.md" card showing only the project's name/description
(static, not editable, not a real file). Separately, the file tree (ADR
0007) only supported folders and links - there was no way to create or edit
an actual text document from inside the app.

## Decision

**A third file-tree node type, `file`,** joins `folder`/`link`. A `file`
node carries editable `content` (text, rendered as Markdown on the
frontend); `link` nodes keep `url`; `folder` nodes carry neither -
enforced by `FileTreeNodeCreateRequest`'s validator, same as the
folder/link split in ADR 0007.

**Every project always has a root-level file node named `SCOPE.md`.**
`POST /projects` creates it alongside the default Kanban board; migration
0017 backfills one for every project that predates this feature (same
backfill pattern as 0012's Kanban board backfill). The Dashboard's README
card is replaced by a card that always looks up `SCOPE.md` specifically
(not "whatever the project's README happens to be") and renders/edits its
content in place - exactly the role `README.md` plays on GitHub's repo page.

`created_by` on `file_tree_nodes` becomes nullable: the SCOPE.md backfill
for pre-existing projects has no real user to attribute it to.

## Consequences

- `PATCH /projects/{id}/tree/{node_id}` edits a file node's content; it
  400s if called on a folder or link node.
- Migration 0017 drops and recreates `file_tree_nodes` rather than altering
  the existing enum in place (Postgres forbids using a value added via
  `ALTER TYPE ... ADD VALUE` in the same transaction) - consistent with this
  repo's precedent of reseeding rather than migrating pre-production tables
  (0009/0013/0014/0015).
- The frontend adds a Markdown-rendering dependency (`react-markdown`) to
  render `file` node content; no other new runtime dependency.
- `SCOPE.md` is a convention enforced at the application layer (fixed name,
  root-level, auto-created), not a database constraint - nothing stops a
  determined API caller from deleting or renaming it. Revisit if that proves
  to be a real problem.
