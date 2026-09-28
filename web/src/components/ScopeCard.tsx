import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  createFileTreeFile,
  listFileTree,
  updateFileTreeContent,
  type FileTreeNodeResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { BookIcon } from "./icons";

const SCOPE_MD_NAME = "SCOPE.md";

export default function ScopeCard({
  projectId,
  refreshKey,
  onChange,
}: {
  projectId: string;
  refreshKey?: number;
  onChange?: () => void;
}) {
  const { token } = useAuth();

  const [scope, setScope] = useState<FileTreeNodeResponse | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isEditing) return;
    if (token && projectId) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, refreshKey]);

  async function load() {
    if (!token) return;
    try {
      const nodes = await listFileTree(token, projectId);
      const found = nodes.find(
        (node) =>
          node.parent_id === null && node.node_type === "file" && node.name === SCOPE_MD_NAME,
      );
      setScope(found ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load SCOPE.md");
    } finally {
      setLoaded(true);
    }
  }

  async function handleCreate() {
    if (!token) return;
    try {
      const created = await createFileTreeFile(token, projectId, SCOPE_MD_NAME, "", null);
      setScope(created);
      setDraft("");
      setIsEditing(true);
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create SCOPE.md");
    }
  }

  function startEditing() {
    setDraft(scope?.content ?? "");
    setIsEditing(true);
  }

  async function handleSave() {
    if (!token || !scope) return;
    try {
      const updated = await updateFileTreeContent(token, projectId, scope.id, draft);
      setScope(updated);
      setIsEditing(false);
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save SCOPE.md");
    }
  }

  return (
    <section className="rounded-md border border-ink-800 bg-ink-900">
      <div className="flex items-center gap-2 border-b border-ink-800 px-4 py-2.5">
        <BookIcon className="h-4 w-4 text-slate-500" />
        <span className="text-sm font-medium text-slate-200">{SCOPE_MD_NAME}</span>
        {scope && !isEditing && (
          <button
            onClick={startEditing}
            className="ml-auto rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
          >
            Edit
          </button>
        )}
        {isEditing && (
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={handleSave}
              className="rounded-md bg-ember-500 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-ember-600"
            >
              Save
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      <div className="px-5 py-4">
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        {isEditing ? (
          <textarea
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={14}
            className="w-full resize-y rounded-md border border-ink-700 bg-ink-850 p-3 font-mono text-sm text-slate-100 outline-none focus:border-ember-500"
          />
        ) : scope?.content ? (
          <div className="markdown-body">
            <ReactMarkdown>{scope.content}</ReactMarkdown>
          </div>
        ) : loaded && !scope ? (
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">No SCOPE.md yet.</p>
            <button
              onClick={handleCreate}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Create SCOPE.md
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            {loaded ? "SCOPE.md is empty." : "Loading..."}
          </p>
        )}
      </div>
    </section>
  );
}
