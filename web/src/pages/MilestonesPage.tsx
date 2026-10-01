import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import { createMilestone, listMilestones, type MilestoneResponse } from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import ProjectTabs from "../components/ProjectTabs";

const inputClass = "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500";

export default function MilestonesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [milestones, setMilestones] = useState<MilestoneResponse[]>([]);
  const [form, setForm] = useState({ title: "", description: "", dueDate: "" });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!token || !projectId) return;
    try { const [projectData, items] = await Promise.all([getProject(token, projectId), listMilestones(token, projectId)]); setProject(projectData); setMilestones(items); setError(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load Milestones"); }
  }
  useEffect(() => { void load(); }, [token, projectId]);

  async function submit() {
    if (!token || !projectId || !form.title.trim()) return;
    try { await createMilestone(token, projectId, { title: form.title.trim(), description: form.description || null, due_date: form.dueDate || null }); setForm({ title: "", description: "", dueDate: "" }); setShowForm(false); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to create Milestone"); }
  }

  if (!project) return <AppShell><p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p></AppShell>;
  return <AppShell breadcrumb={project.name}><ProjectTabs projectId={project.id} /><main className="mx-auto max-w-5xl space-y-4 p-6">
    <div className="flex items-center justify-between"><div><h1 className="text-xl font-semibold text-slate-100">Milestones</h1><p className="text-sm text-slate-500">Organize top-level Tasks into project outcomes.</p></div><button className="rounded-md bg-ember-500 px-3 py-2 text-sm font-medium text-white" onClick={() => setShowForm((v) => !v)}>New Milestone</button></div>
    {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
    {showForm && <section aria-label="Create Milestone" className="grid gap-2 rounded-md border border-ink-800 bg-ink-900 p-4 md:grid-cols-3"><input aria-label="Title" placeholder="Milestone title" className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /><input aria-label="Description" placeholder="Description" className={inputClass} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /><input aria-label="Due date" type="date" className={inputClass} value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} /><button className="rounded-md bg-ember-500 px-3 py-2 text-sm text-white md:col-span-3" onClick={() => void submit()}>Create Milestone</button></section>}
    <div className="overflow-hidden rounded-md border border-ink-800 bg-ink-900"><table className="w-full text-left text-sm"><thead className="border-b border-ink-800 text-xs uppercase text-slate-500"><tr>{["Title","Status","Due date","Completed Tasks","Progress"].map((h) => <th key={h} className="px-4 py-2">{h}</th>)}</tr></thead><tbody className="divide-y divide-ink-800">{milestones.map((m) => <tr key={m.id}><td className="px-4 py-3"><Link className="font-medium text-slate-100 hover:text-ember-400" to={`/projects/${projectId}/milestones/${m.id}`}>{m.title}</Link></td><td className="px-4 capitalize text-slate-300">{m.status}</td><td className="px-4 text-slate-400">{m.due_date ?? "—"}</td><td className="px-4 text-slate-300">{m.completed_tasks} / {m.total_tasks}</td><td className="px-4"><div className="flex items-center gap-2"><div className="h-2 w-24 overflow-hidden rounded-full bg-ink-700"><div className="h-full bg-ember-500" style={{ width: `${m.progress_percentage}%` }} /></div><span>{Math.round(m.progress_percentage)}%</span></div></td></tr>)}</tbody></table>{milestones.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No Milestones yet.</p>}</div>
  </main></AppShell>;
}
