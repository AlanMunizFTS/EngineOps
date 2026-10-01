import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, listProjectMembers, type ProjectMemberDetailResponse, type ProjectResponse } from "../api/client";
import {
  attachTaskLabel, createTask, listMilestones, listProjectLabels, listProjectTasks,
  type LabelResponse, type MilestoneResponse, type TaskPriority, type TaskResponse,
  type TaskStatus, type TaskType,
} from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { PriorityBadge, StatusBadge } from "../components/TaskBadges";
import ProjectTabs from "../components/ProjectTabs";

const STATUSES: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];
const TYPES: TaskType[] = ["task", "bug", "improvement", "incident"];
const inputClass = "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500";

export default function TasksPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [milestones, setMilestones] = useState<MilestoneResponse[]>([]);
  const [labels, setLabels] = useState<LabelResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [filters, setFilters] = useState({ status: "", priority: "", taskType: "", milestoneId: "", assigneeId: "" });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", status: "backlog" as TaskStatus, priority: "medium" as TaskPriority, taskType: "task" as TaskType, milestoneId: "", assigneeId: "", startDate: "", dueDate: "", labelId: "" });
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      setError(null);
      const [projectData, taskData, milestoneData, labelData, memberData] = await Promise.all([
        getProject(token, projectId),
        listProjectTasks(token, projectId, {
          status: (filters.status || undefined) as TaskStatus | undefined,
          priority: (filters.priority || undefined) as TaskPriority | undefined,
          task_type: (filters.taskType || undefined) as TaskType | undefined,
          milestone_id: filters.milestoneId || undefined,
          assignee_id: filters.assigneeId || undefined,
        }),
        listMilestones(token, projectId), listProjectLabels(token, projectId), listProjectMembers(token, projectId),
      ]);
      setProject(projectData);
      setTasks(taskData.filter((task) => task.parent_task_id === null));
      setMilestones(milestoneData); setLabels(labelData); setMembers(memberData);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load tasks"); }
  }

  useEffect(() => { void loadAll(); }, [token, projectId, filters.status, filters.priority, filters.taskType, filters.milestoneId, filters.assigneeId]);
  const milestoneNames = useMemo(() => new Map(milestones.map((m) => [m.id, m.title])), [milestones]);
  const memberNames = useMemo(() => new Map(members.map((m) => [m.user_id, m.full_name])), [members]);

  async function submitTask() {
    if (!token || !projectId || !form.title.trim()) return;
    try {
      setError(null);
      const created = await createTask(token, projectId, {
        title: form.title.trim(), description: form.description || null, status: form.status,
        priority: form.priority, task_type: form.taskType, milestone_id: form.milestoneId || null,
        assignee_id: form.assigneeId || null, start_date: form.startDate || null, due_date: form.dueDate || null,
      });
      if (form.labelId) await attachTaskLabel(token, created.id, form.labelId);
      setForm({ title: "", description: "", status: "backlog", priority: "medium", taskType: "task", milestoneId: "", assigneeId: "", startDate: "", dueDate: "", labelId: "" });
      setShowForm(false); await loadAll();
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to create task"); }
  }

  if (!project) return <AppShell><p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p></AppShell>;
  const filter = (key: keyof typeof filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  const field = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  return <AppShell breadcrumb={project.name}>
    <ProjectTabs projectId={project.id} />
    <div className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="flex items-center justify-between"><div><h1 className="text-xl font-semibold text-slate-100">Tasks</h1><p className="text-sm text-slate-500">Top-level executable work for this project.</p></div><button onClick={() => setShowForm((v) => !v)} className="rounded-md bg-ember-500 px-3 py-2 text-sm font-medium text-white hover:bg-ember-600">New Task</button></div>
      {error && <p role="alert" className="rounded-md border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <select aria-label="Filter by status" className={inputClass} value={filters.status} onChange={(e) => filter("status", e.target.value)}><option value="">All statuses</option>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Filter by priority" className={inputClass} value={filters.priority} onChange={(e) => filter("priority", e.target.value)}><option value="">All priorities</option>{PRIORITIES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Filter by type" className={inputClass} value={filters.taskType} onChange={(e) => filter("taskType", e.target.value)}><option value="">All types</option>{TYPES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Filter by milestone" className={inputClass} value={filters.milestoneId} onChange={(e) => filter("milestoneId", e.target.value)}><option value="">All milestones</option>{milestones.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select>
        <select aria-label="Filter by assignee" className={inputClass} value={filters.assigneeId} onChange={(e) => filter("assigneeId", e.target.value)}><option value="">All assignees</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}</select>
      </div>
      {showForm && <section aria-label="Create Task" className="grid gap-3 rounded-md border border-ink-800 bg-ink-900 p-4 md:grid-cols-4">
        <input aria-label="Title" className={`${inputClass} md:col-span-2`} placeholder="Task title" value={form.title} onChange={(e) => field("title", e.target.value)} />
        <select aria-label="Status" className={inputClass} value={form.status} onChange={(e) => field("status", e.target.value)}>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Priority" className={inputClass} value={form.priority} onChange={(e) => field("priority", e.target.value)}>{PRIORITIES.map((x) => <option key={x}>{x}</option>)}</select>
        <textarea aria-label="Description" className={`${inputClass} md:col-span-2`} placeholder="Description" value={form.description} onChange={(e) => field("description", e.target.value)} />
        <select aria-label="Task type" className={inputClass} value={form.taskType} onChange={(e) => field("taskType", e.target.value)}>{TYPES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Milestone" className={inputClass} value={form.milestoneId} onChange={(e) => field("milestoneId", e.target.value)}><option value="">No milestone</option>{milestones.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select>
        <select aria-label="Assignee" className={inputClass} value={form.assigneeId} onChange={(e) => field("assigneeId", e.target.value)}><option value="">Unassigned</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}</select>
        <input aria-label="Start date" type="date" className={inputClass} value={form.startDate} onChange={(e) => field("startDate", e.target.value)} />
        <input aria-label="Due date" type="date" className={inputClass} value={form.dueDate} onChange={(e) => field("dueDate", e.target.value)} />
        <select aria-label="Label" className={inputClass} value={form.labelId} onChange={(e) => field("labelId", e.target.value)}><option value="">No label</option>{labels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select>
        <button onClick={() => void submitTask()} className="rounded-md bg-ember-500 px-3 py-2 text-sm font-medium text-white">Create Task</button>
      </section>}
      <div className="overflow-x-auto rounded-md border border-ink-800 bg-ink-900"><table className="w-full text-left text-sm"><thead className="border-b border-ink-800 text-xs uppercase text-slate-500"><tr>{["Task","Status","Priority","Type","Milestone","Assignee","Start","Due","Subtasks"].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead><tbody className="divide-y divide-ink-800">{tasks.map((task) => <tr key={task.id} className="hover:bg-ink-800/70"><td className="px-3 py-3"><Link className="font-medium text-slate-100 hover:text-ember-400" to={`/projects/${projectId}/tasks/${task.id}`}>{task.title}</Link></td><td className="px-3"><StatusBadge status={task.status} /></td><td className="px-3"><PriorityBadge priority={task.priority} /></td><td className="px-3 text-slate-400">{task.task_type}</td><td className="px-3 text-slate-400">{task.milestone_id ? milestoneNames.get(task.milestone_id) ?? "—" : "—"}</td><td className="px-3 text-slate-400">{task.assignee_id ? memberNames.get(task.assignee_id) ?? "—" : "—"}</td><td className="px-3 text-slate-400">{task.start_date ?? "—"}</td><td className="px-3 text-slate-400">{task.due_date ?? "—"}</td><td className="px-3 text-slate-300">{task.subtasks_completed} / {task.subtasks_total}</td></tr>)}</tbody></table>{tasks.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No Tasks match these filters.</p>}</div>
    </div>
  </AppShell>;
}
