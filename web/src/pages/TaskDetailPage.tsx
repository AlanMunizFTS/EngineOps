import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, listProjectMembers, type AuditLogEntryResponse, type ProjectMemberDetailResponse, type ProjectResponse } from "../api/client";
import {
  attachTaskLabel, createSubtask, createTaskComment, deleteTask, detachTaskLabel, getTask,
  getTaskHistory, listMilestones, listProjectLabels, listSubtasks, listTaskComments, updateTask,
  updateTaskStatus, type LabelResponse, type MilestoneResponse, type TaskCommentResponse,
  type TaskPriority, type TaskResponse, type TaskStatus, type TaskType,
} from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { LabelChip, PriorityBadge, StatusBadge } from "../components/TaskBadges";
import ProjectTabs from "../components/ProjectTabs";

const STATUSES: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];
const TYPES: TaskType[] = ["task", "bug", "improvement", "incident"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];
const inputClass = "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500";

export default function TaskDetailPage() {
  const { projectId, taskId } = useParams<{ projectId: string; taskId: string }>();
  const { token } = useAuth();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [parent, setParent] = useState<TaskResponse | null>(null);
  const [subtasks, setSubtasks] = useState<TaskResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [milestones, setMilestones] = useState<MilestoneResponse[]>([]);
  const [labels, setLabels] = useState<LabelResponse[]>([]);
  const [comments, setComments] = useState<TaskCommentResponse[]>([]);
  const [history, setHistory] = useState<AuditLogEntryResponse[]>([]);
  const [form, setForm] = useState({ title: "", description: "", priority: "medium" as TaskPriority, taskType: "task" as TaskType, milestoneId: "", assigneeId: "", startDate: "", dueDate: "" });
  const [newSubtask, setNewSubtask] = useState({ title: "", description: "", assigneeId: "", startDate: "", dueDate: "" });
  const [commentBody, setCommentBody] = useState("");
  const [labelToAdd, setLabelToAdd] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    if (!token || !projectId || !taskId) return;
    try {
      setError(null);
      const [projectData, taskData, memberData, milestoneData, labelData, commentData, historyData] = await Promise.all([
        getProject(token, projectId), getTask(token, taskId), listProjectMembers(token, projectId),
        listMilestones(token, projectId), listProjectLabels(token, projectId), listTaskComments(token, taskId), getTaskHistory(token, taskId),
      ]);
      setProject(projectData); setTask(taskData); setMembers(memberData); setMilestones(milestoneData);
      setLabels(labelData); setComments(commentData); setHistory(historyData);
      setForm({ title: taskData.title, description: taskData.description ?? "", priority: taskData.priority, taskType: taskData.task_type, milestoneId: taskData.milestone_id ?? "", assigneeId: taskData.assignee_id ?? "", startDate: taskData.start_date ?? "", dueDate: taskData.due_date ?? "" });
      const [children, parentData] = await Promise.all([
        taskData.parent_task_id ? Promise.resolve([]) : listSubtasks(token, taskData.id),
        taskData.parent_task_id ? getTask(token, taskData.parent_task_id) : Promise.resolve(null),
      ]);
      setSubtasks(children); setParent(parentData);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load Task"); }
  }

  useEffect(() => { void loadAll(); }, [token, projectId, taskId]);
  const membersById = useMemo(() => new Map(members.map((m) => [m.user_id, m.full_name])), [members]);
  const availableLabels = labels.filter((label) => !task?.labels.some((attached) => attached.id === label.id));

  async function saveTask() {
    if (!token || !task) return;
    try {
      const updated = await updateTask(token, task.id, {
        title: form.title, description: form.description || null, priority: form.priority, task_type: form.taskType,
        milestone_id: task.parent_task_id ? undefined : form.milestoneId || null, assignee_id: form.assigneeId || null,
        start_date: form.startDate || null, due_date: form.dueDate || null,
      });
      setTask(updated); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to save Task"); }
  }

  async function setStatus(target: TaskResponse, status: TaskStatus) {
    if (!token) return;
    try {
      const updated = await updateTaskStatus(token, target.id, status);
      if (target.id === task?.id) setTask(updated);
      else setSubtasks((current) => current.map((item) => item.id === updated.id ? updated : item));
      setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to update Task status"); await loadAll(); }
  }

  async function addSubtask() {
    if (!token || !task || !newSubtask.title.trim()) return;
    try {
      const created = await createSubtask(token, task.id, { title: newSubtask.title.trim(), description: newSubtask.description || null, assignee_id: newSubtask.assigneeId || null, start_date: newSubtask.startDate || null, due_date: newSubtask.dueDate || null });
      setSubtasks((current) => [...current, created]);
      setTask((current) => current ? { ...current, subtasks_total: current.subtasks_total + 1 } : current);
      setNewSubtask({ title: "", description: "", assigneeId: "", startDate: "", dueDate: "" }); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to create Subtask"); }
  }

  async function removeSubtask(subtask: TaskResponse) {
    if (!token || !window.confirm(`Delete Subtask “${subtask.title}”?`)) return;
    try { await deleteTask(token, subtask.id); await loadAll(); } catch (err) { setError(err instanceof Error ? err.message : "Failed to delete Subtask"); }
  }

  async function addComment() {
    if (!token || !task || !commentBody.trim()) return;
    try { const created = await createTaskComment(token, task.id, commentBody.trim()); setComments((items) => [...items, created]); setCommentBody(""); } catch (err) { setError(err instanceof Error ? err.message : "Failed to add comment"); }
  }

  if (!project || !task) return <AppShell><p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p></AppShell>;
  const field = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const subField = (key: keyof typeof newSubtask, value: string) => setNewSubtask((current) => ({ ...current, [key]: value }));

  return <AppShell breadcrumb={`${project.name} / ${task.title}`}>
    <ProjectTabs projectId={project.id} />
    <main className="mx-auto max-w-6xl space-y-5 p-6">
      {parent && <p className="text-sm text-slate-400">Subtask of <Link className="text-ember-400 hover:underline" to={`/projects/${projectId}/tasks/${parent.id}`}>{parent.title}</Link></p>}
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">{task.parent_task_id ? "Subtask" : "Task"}</p><h1 className="text-2xl font-semibold text-slate-100">{task.title}</h1></div><div className="flex gap-2"><StatusBadge status={task.status} /><PriorityBadge priority={task.priority} /></div></div>
      {error && <p role="alert" className="rounded-md border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}

      <section className="grid gap-3 rounded-md border border-ink-800 bg-ink-900 p-4 md:grid-cols-4">
        <input aria-label="Title" className={`${inputClass} md:col-span-2`} value={form.title} onChange={(e) => field("title", e.target.value)} />
        <select aria-label="Status" className={inputClass} value={task.status} onChange={(e) => void setStatus(task, e.target.value as TaskStatus)}>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
        <select aria-label="Priority" className={inputClass} value={form.priority} onChange={(e) => field("priority", e.target.value)}>{PRIORITIES.map((x) => <option key={x}>{x}</option>)}</select>
        <textarea aria-label="Description" className={`${inputClass} md:col-span-2`} value={form.description} onChange={(e) => field("description", e.target.value)} />
        <select aria-label="Task type" className={inputClass} value={form.taskType} onChange={(e) => field("taskType", e.target.value)}>{TYPES.map((x) => <option key={x}>{x}</option>)}</select>
        {!task.parent_task_id && <select aria-label="Milestone" className={inputClass} value={form.milestoneId} onChange={(e) => field("milestoneId", e.target.value)}><option value="">No milestone</option>{milestones.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select>}
        <select aria-label="Assignee" className={inputClass} value={form.assigneeId} onChange={(e) => field("assigneeId", e.target.value)}><option value="">Unassigned</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}</select>
        <input aria-label="Start date" type="date" className={inputClass} value={form.startDate} onChange={(e) => field("startDate", e.target.value)} />
        <input aria-label="Due date" type="date" className={inputClass} value={form.dueDate} onChange={(e) => field("dueDate", e.target.value)} />
        <button className="rounded-md bg-ember-500 px-3 py-2 text-sm font-medium text-white" onClick={() => void saveTask()}>Save</button>
      </section>

      <section className="rounded-md border border-ink-800 bg-ink-900 p-4"><h2 className="mb-3 text-sm font-semibold text-slate-100">Labels</h2><div className="flex flex-wrap gap-2">{task.labels.map((label) => <button key={label.id} title="Remove label" onClick={async () => { if (!token) return; setTask(await detachTaskLabel(token, task.id, label.id)); }}><LabelChip label={label} /></button>)}<select aria-label="Add label" className={inputClass} value={labelToAdd} onChange={async (e) => { const value = e.target.value; setLabelToAdd(value); if (token && value) { setTask(await attachTaskLabel(token, task.id, value)); setLabelToAdd(""); } }}><option value="">Add label…</option>{availableLabels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></div></section>

      {!task.parent_task_id && <section className="space-y-3 rounded-md border border-ink-800 bg-ink-900 p-4">
        <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-100">Subtasks</h2><p className="text-xs text-slate-500">{subtasks.filter((s) => s.status === "done").length} / {subtasks.length} completed</p></div></div>
        <div className="divide-y divide-ink-800 rounded-md border border-ink-800">{subtasks.map((subtask) => <div key={subtask.id} className="flex items-center gap-3 p-3"><input aria-label={`Complete ${subtask.title}`} type="checkbox" checked={subtask.status === "done"} onChange={(e) => void setStatus(subtask, e.target.checked ? "done" : "todo")} /><Link className="min-w-0 flex-1 truncate text-sm text-slate-200 hover:text-ember-400" to={`/projects/${projectId}/tasks/${subtask.id}`}>{subtask.title}</Link><span className="hidden text-xs text-slate-500 sm:inline">{subtask.assignee_id ? membersById.get(subtask.assignee_id) ?? "Unassigned" : "Unassigned"}</span><StatusBadge status={subtask.status} /><button aria-label={`Delete ${subtask.title}`} className="text-xs text-red-400 hover:text-red-300" onClick={() => void removeSubtask(subtask)}>Delete</button></div>)}</div>
        <div className="grid gap-2 md:grid-cols-5"><input aria-label="Subtask title" className={inputClass} placeholder="New Subtask" value={newSubtask.title} onChange={(e) => subField("title", e.target.value)} /><input aria-label="Subtask description" className={inputClass} placeholder="Description" value={newSubtask.description} onChange={(e) => subField("description", e.target.value)} /><select aria-label="Subtask assignee" className={inputClass} value={newSubtask.assigneeId} onChange={(e) => subField("assigneeId", e.target.value)}><option value="">Unassigned</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name}</option>)}</select><input aria-label="Subtask start date" type="date" className={inputClass} value={newSubtask.startDate} onChange={(e) => subField("startDate", e.target.value)} /><input aria-label="Subtask due date" type="date" className={inputClass} value={newSubtask.dueDate} onChange={(e) => subField("dueDate", e.target.value)} /><button className="rounded-md border border-ember-500 px-3 py-2 text-sm text-ember-400 md:col-span-5" onClick={() => void addSubtask()}>+ Add Subtask</button></div>
      </section>}

      <section className="rounded-md border border-ink-800 bg-ink-900 p-4"><h2 className="mb-3 text-sm font-semibold text-slate-100">Comments</h2><div className="space-y-2">{comments.map((comment) => <div key={comment.id} className="rounded bg-ink-800 p-3 text-sm text-slate-300"><p>{comment.body}</p><time className="mt-1 block text-xs text-slate-500">{new Date(comment.created_at).toLocaleString()}</time></div>)}</div><div className="mt-3 flex gap-2"><input aria-label="Comment" className={`${inputClass} flex-1`} value={commentBody} onChange={(e) => setCommentBody(e.target.value)} placeholder="Add a comment" /><button className="rounded-md bg-ember-500 px-3 text-sm text-white" onClick={() => void addComment()}>Comment</button></div></section>
      <section className="rounded-md border border-ink-800 bg-ink-900 p-4"><h2 className="mb-3 text-sm font-semibold text-slate-100">History</h2><div className="space-y-2">{history.map((entry) => <div key={entry.id} className="flex justify-between text-sm"><span className="text-slate-300">{entry.action.replace(/_/g, " ")}</span><time className="text-xs text-slate-500">{new Date(entry.occurred_at).toLocaleString()}</time></div>)}</div></section>
    </main>
  </AppShell>;
}
