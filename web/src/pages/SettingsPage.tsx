import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  addProjectMember,
  deleteProject,
  getProject,
  listMemberCandidates,
  listProjectMembers,
  removeProjectMember,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
  type UserSummaryResponse,
} from "../api/client";
import { deleteTask, listProjectTasks, type TaskResponse } from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { PriorityBadge, StatusBadge } from "../components/TaskBadges";
import ProjectTabs from "../components/ProjectTabs";
import { TrashIcon } from "../components/icons";

export default function SettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { token, user } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [candidates, setCandidates] = useState<UserSummaryResponse[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDeletingProject, setIsDeletingProject] = useState(false);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, taskData, memberData, candidateData] = await Promise.all([
        getProject(token, projectId),
        listProjectTasks(token, projectId),
        listProjectMembers(token, projectId),
        listMemberCandidates(token, projectId),
      ]);
      setProject(projectData);
      setTasks(taskData);
      setMembers(memberData);
      setCandidates(candidateData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    }
  }

  async function handleDeleteTask(task: TaskResponse) {
    if (!token) return;
    if (!window.confirm(`Delete "${task.title}"? This can't be undone.`)) return;
    try {
      await deleteTask(token, task.id);
      setTasks((current) => current.filter((i) => i.id !== task.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete task");
    }
  }

  async function handleAddMember() {
    if (!token || !projectId || !selectedCandidateId) return;
    try {
      await addProjectMember(token, projectId, selectedCandidateId);
      const candidate = candidates.find((c) => c.id === selectedCandidateId);
      setSelectedCandidateId("");
      setCandidates((current) => current.filter((c) => c.id !== selectedCandidateId));
      if (candidate) {
        setMembers((current) => [
          ...current,
          {
            project_id: projectId,
            user_id: candidate.id,
            project_role: "contributor",
            added_at: new Date().toISOString(),
            email: candidate.email,
            full_name: candidate.full_name,
          },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    }
  }

  async function handleRemoveMember(member: ProjectMemberDetailResponse) {
    if (!token || !projectId) return;
    if (!window.confirm(`Remove ${member.full_name} from this project?`)) return;
    try {
      await removeProjectMember(token, projectId, member.user_id);
      setMembers((current) => current.filter((m) => m.user_id !== member.user_id));
      setCandidates((current) => [
        ...current,
        { id: member.user_id, email: member.email, full_name: member.full_name },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  }

  async function handleDeleteProject() {
    if (!token || !projectId || !project) return;
    const confirmed = window.confirm(
      `Delete project "${project.name}"? All of its tasks, boards, materials, files, and history will be permanently deleted. This can't be undone.`,
    );
    if (!confirmed) return;

    setIsDeletingProject(true);
    setError(null);
    try {
      await deleteProject(token, projectId);
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete project");
      setIsDeletingProject(false);
    }
  }

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  const canDeleteProject =
    user?.roles.includes("admin") ||
    members.some((member) => member.user_id === user?.id && member.project_role === "owner");

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-5xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <section>
          <h2 className="mb-1 text-sm font-semibold text-slate-100">Members</h2>
          <p className="mb-3 text-xs text-slate-500">
            Only members of this project can be assigned activities in Schedule and Kanban.
          </p>
          <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
            {members.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No members added yet.</p>
            ) : (
              members.map((member) => (
                <div
                  key={member.user_id}
                  className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
                >
                  <span className="text-slate-100">{member.full_name}</span>
                  <span className="text-xs text-slate-500">{member.email}</span>
                  <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[11px] uppercase text-slate-400">
                    {member.project_role}
                  </span>
                  <button
                    onClick={() => void handleRemoveMember(member)}
                    title="Remove member"
                    className="ml-auto text-slate-600 hover:text-red-400"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <select
              value={selectedCandidateId}
              onChange={(e) => setSelectedCandidateId(e.target.value)}
              className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            >
              <option value="">
                {candidates.length === 0 ? "No users available to add" : "Select a user…"}
              </option>
              {candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name} ({candidate.email})
                </option>
              ))}
            </select>
            <button
              onClick={() => void handleAddMember()}
              disabled={!selectedCandidateId}
              className="rounded-md bg-ember-500 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-ember-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add member
            </button>
          </div>
        </section>

        <section>
          <h2 className="mb-1 text-sm font-semibold text-slate-100">Tasks</h2>
          <p className="mb-3 text-xs text-slate-500">
            Standalone Tasks and Subtasks can be deleted. A Task containing Subtasks cannot be
            deleted until those Subtasks are moved or deleted.
          </p>
          <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
            {tasks.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No tasks in this project yet.</p>
            ) : (
              tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
                >
                  <StatusBadge status={task.status} />
                  <Link
                    to={`/projects/${projectId}/tasks/${task.id}`}
                    className="text-slate-100 hover:text-ember-400 hover:underline"
                  >
                    {task.title}
                  </Link>
                  <PriorityBadge priority={task.priority} />
                  <button
                    onClick={() => void handleDeleteTask(task)}
                    disabled={task.subtasks_total > 0}
                    title="Delete task"
                    className="ml-auto text-slate-600 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                  {task.subtasks_total > 0 && <span className="text-xs text-slate-500">This Task contains Subtasks.</span>}
                </div>
              ))
            )}
          </div>
        </section>

        {canDeleteProject && (
          <section className="rounded-md border border-red-900/70 bg-red-950/20 p-4">
            <h2 className="mb-1 text-sm font-semibold text-red-300">Danger zone</h2>
            <p className="mb-3 text-xs text-slate-400">
              Permanently delete this project and all of its tasks, boards, materials, files,
              members, and history. This action cannot be undone.
            </p>
            <button
              type="button"
              onClick={() => void handleDeleteProject()}
              disabled={isDeletingProject}
              className="rounded-md border border-red-700 bg-red-950/60 px-3 py-1.5 text-sm font-medium text-red-300 transition-colors hover:bg-red-900/60 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDeletingProject ? "Deleting project..." : "Delete project"}
            </button>
          </section>
        )}
      </div>
    </AppShell>
  );
}
