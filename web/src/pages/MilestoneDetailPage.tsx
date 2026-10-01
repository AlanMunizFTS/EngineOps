import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import { deleteMilestone, getMilestone, listProjectTasks, updateMilestone, type MilestoneResponse, type TaskResponse } from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { PriorityBadge, StatusBadge } from "../components/TaskBadges";
import ProjectTabs from "../components/ProjectTabs";

const inputClass = "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500";

export default function MilestoneDetailPage() {
  const { projectId, milestoneId } = useParams<{ projectId: string; milestoneId: string }>();
  const { token } = useAuth(); const navigate = useNavigate();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [milestone, setMilestone] = useState<MilestoneResponse | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [form, setForm] = useState({ title: "", description: "", status: "open", dueDate: "" });
  const [error, setError] = useState<string | null>(null);
  async function load() { if (!token || !projectId || !milestoneId) return; try { const [p, m, items] = await Promise.all([getProject(token, projectId), getMilestone(token, milestoneId), listProjectTasks(token, projectId, { milestone_id: milestoneId })]); setProject(p); setMilestone(m); setTasks(items.filter((task) => task.parent_task_id === null)); setForm({ title: m.title, description: m.description ?? "", status: m.status, dueDate: m.due_date ?? "" }); setError(null); } catch (err) { setError(err instanceof Error ? err.message : "Failed to load Milestone"); } }
  useEffect(() => { void load(); }, [token, projectId, milestoneId]);
  if (!project || !milestone) return <AppShell><p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p></AppShell>;
  return <AppShell breadcrumb={`${project.name} / ${milestone.title}`}><ProjectTabs projectId={project.id} /><main className="mx-auto max-w-5xl space-y-5 p-6">
    <div className="flex justify-between"><div><p className="text-xs uppercase tracking-wide text-slate-500">Milestone</p><h1 className="text-2xl font-semibold text-slate-100">{milestone.title}</h1></div><button className="text-sm text-red-400" onClick={async () => { if (!token || !window.confirm("Delete this Milestone? Tasks will remain unassigned.")) return; try { await deleteMilestone(token, milestone.id); navigate(`/projects/${projectId}/milestones`); } catch (err) { setError(err instanceof Error ? err.message : "Failed to delete Milestone"); } }}>Delete</button></div>
    {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
    <section className="grid gap-3 rounded-md border border-ink-800 bg-ink-900 p-4 md:grid-cols-2"><input aria-label="Title" className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /><select aria-label="Status" className={inputClass} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="open">open</option><option value="closed">closed</option></select><textarea aria-label="Description" className={inputClass} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /><input aria-label="Due date" type="date" className={inputClass} value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} /><button className="rounded-md bg-ember-500 px-3 py-2 text-sm text-white md:col-span-2" onClick={async () => { if (!token) return; try { setMilestone(await updateMilestone(token, milestone.id, { title: form.title, description: form.description || null, status: form.status as "open" | "closed", due_date: form.dueDate || null })); setError(null); } catch (err) { setError(err instanceof Error ? err.message : "Failed to save Milestone"); } }}>Save Milestone</button></section>
    <section className="rounded-md border border-ink-800 bg-ink-900 p-4"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-100">Progress</h2><p className="text-xs text-slate-500">{milestone.completed_tasks} / {milestone.total_tasks} top-level Tasks</p></div><span className="text-xl font-semibold text-ember-400">{Math.round(milestone.progress_percentage)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-ink-700"><div className="h-full bg-ember-500" style={{ width: `${milestone.progress_percentage}%` }} /></div></section>
    <section className="rounded-md border border-ink-800 bg-ink-900 p-4"><h2 className="mb-3 text-sm font-semibold text-slate-100">Tasks</h2><div className="divide-y divide-ink-800">{tasks.map((task) => <Link key={task.id} to={`/projects/${projectId}/tasks/${task.id}`} className="flex items-center gap-3 py-3 hover:text-ember-400"><span className="flex-1 text-sm text-slate-200">{task.title}</span><PriorityBadge priority={task.priority} /><StatusBadge status={task.status} /><span className="text-xs text-slate-500">{task.subtasks_completed} / {task.subtasks_total} Subtasks</span></Link>)}{tasks.length === 0 && <p className="py-4 text-sm text-slate-500">No Tasks assigned.</p>}</div></section>
  </main></AppShell>;
}
