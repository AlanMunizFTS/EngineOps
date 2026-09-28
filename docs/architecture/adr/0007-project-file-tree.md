# ADR 0007: Project file tree is folders + external links, not real file storage

## Status

Accepted.

## Context

The Dashboard tab needed a GitHub-style file browser: folders that can be
created ad hoc, and entries pointing at presentations/documents/other
artifacts. The platform already provisions MinIO (S3-compatible) in
`docker-compose.yml`, so real file upload/storage was an option, but nothing
today writes to it - it's infrastructure reserved for a later, unspecified
need.

## Decision

The file tree stores **folders and links only** - one table
(`file_tree_nodes`), self-referencing via `parent_id` (`ON DELETE CASCADE`,
so deleting a folder deletes its subtree). A `link` node always carries a
`url` (validated at the API layer: `FileTreeNodeCreateRequest` requires `url`
for links and forbids it for folders); a `folder` node never does. No binary
content is stored or proxied by this platform - a "file" in the tree is a
pointer to wherever it actually lives (SharePoint, Drive, Confluence, etc.).

MinIO integration for real uploads is deferred - if/when actual file storage
is needed, it should be a new `StoragePort`/adapter added deliberately, not
retrofitted onto this table.

## Consequences

- Simple schema: no content-type, size, or storage-key columns to keep in
  sync with an object store.
- `FileTreeRepository` (port) / `SqlAlchemyFileTreeRepository` (adapter)
  follow the same Ports & Adapters shape as every other project-scoped
  resource (labels, milestones, issues) - see CLAUDE.md §6.
- If binary upload is added later, it likely becomes a second node type
  (e.g. `file`) with its own storage-backed fields, additive to this schema
  rather than a rewrite.
