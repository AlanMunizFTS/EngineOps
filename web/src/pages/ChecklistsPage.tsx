import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  addProjectChecklistItem,
  createProjectChecklist,
  deleteProjectChecklist,
  deleteProjectChecklistItem,
  listProjectChecklists,
  type ProjectChecklistResponse,
} from "../api/client_checklists";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import ProjectTabs from "../components/ProjectTabs";

const INPUT_CLASS = "rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500";

export default function ChecklistsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [checklists, setChecklists] = useState<ProjectChecklistResponse[]>([]);
  const [newName, setNewName] = useState("");
  const [itemDrafts, setItemDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, checklistData] = await Promise.all([
        getProject(token, projectId),
        listProjectChecklists(token, projectId),
      ]);
      setProject(projectData);
      setChecklists(checklistData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load checklists");
    }
  }

  useEffect(() => { void loadAll(); }, [token, projectId]);

  async function createChecklist() {
    if (!token || !projectId || !newName.trim()) return;
    try {
      const created = await createProjectChecklist(token, projectId, newName.trim());
      setChecklists((current) => [...current, created]);
      setNewName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create checklist");
    }
  }

  async function addItem(checklistId: string) {
    if (!token || !itemDrafts[checklistId]?.trim()) return;
    try {
      const item = await addProjectChecklistItem(token, checklistId, itemDrafts[checklistId].trim());
      setChecklists((current) => current.map((checklist) =>
        checklist.id === checklistId
          ? { ...checklist, items: [...checklist.items, item] }
          : checklist,
      ));
      setItemDrafts((current) => ({ ...current, [checklistId]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add checklist item");
    }
  }

  async function removeItem(checklistId: string, itemId: string) {
    if (!token) return;
    await deleteProjectChecklistItem(token, itemId);
    setChecklists((current) => current.map((checklist) =>
      checklist.id === checklistId
        ? { ...checklist, items: checklist.items.filter((item) => item.id !== itemId) }
        : checklist,
    ));
  }

  async function removeChecklist(checklist: ProjectChecklistResponse) {
    if (!token || !window.confirm(`Delete checklist "${checklist.name}"?`)) return;
    await deleteProjectChecklist(token, checklist.id);
    setChecklists((current) => current.filter((item) => item.id !== checklist.id));
  }

  if (!project) return <AppShell><p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p></AppShell>;

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />
      <main className="mx-auto max-w-5xl space-y-5 p-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Checklists</h1>
          <p className="text-sm text-slate-500">Create reusable checklists and attach them to project tasks.</p>
        </div>
        {error && <p role="alert" className="rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
        <div className="flex gap-2 rounded-md border border-ink-800 bg-ink-900 p-4">
          <input aria-label="Checklist name" value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="New checklist name" className={`${INPUT_CLASS} flex-1`} />
          <button onClick={() => void createChecklist()} className="rounded-md bg-ember-500 px-4 py-2 text-sm font-medium text-white">Create checklist</button>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {checklists.map((checklist) => (
            <section key={checklist.id} className="rounded-md border border-ink-800 bg-ink-900 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="font-semibold text-slate-100">{checklist.name}</h2>
                <button onClick={() => void removeChecklist(checklist)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
              </div>
              <ul className="mb-3 space-y-2">
                {checklist.items.map((item) => (
                  <li key={item.id} className="flex items-start gap-2 rounded bg-ink-800 px-3 py-2 text-sm text-slate-300">
                    <span className="mt-1 h-3 w-3 shrink-0 rounded-sm border border-slate-500" />
                    <span className="flex-1">{item.content}</span>
                    <button aria-label={`Delete ${item.content}`} onClick={() => void removeItem(checklist.id, item.id)} className="text-red-400">×</button>
                  </li>
                ))}
                {checklist.items.length === 0 && <li className="text-sm text-slate-500">No items yet.</li>}
              </ul>
              <div className="flex gap-2">
                <input aria-label={`New item for ${checklist.name}`} value={itemDrafts[checklist.id] ?? ""} onChange={(event) => setItemDrafts((current) => ({ ...current, [checklist.id]: event.target.value }))} placeholder="Checklist item" className={`${INPUT_CLASS} min-w-0 flex-1`} />
                <button onClick={() => void addItem(checklist.id)} className="rounded-md border border-ember-500 px-3 py-2 text-sm text-ember-400">Add</button>
              </div>
            </section>
          ))}
        </div>
        {checklists.length === 0 && <p className="rounded-md border border-dashed border-ink-700 p-8 text-center text-sm text-slate-500">No project checklists yet.</p>}
      </main>
    </AppShell>
  );
}
