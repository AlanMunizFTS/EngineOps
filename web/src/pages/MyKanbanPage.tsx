import { useEffect, useMemo, useState } from "react";

import { listProjects, type ProjectResponse } from "../api/client";
import {
  createIssue,
  listMyPendingIssues,
  updateIssueStatus,
  type IssuePriority,
  type IssueResponse,
  type IssueStatus,
  type IssueType,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { PlusIcon } from "../components/icons";
import Modal, { ModalActions } from "../components/Modal";
import PersonalKanbanBoard from "../components/PersonalKanbanBoard";

const INPUT_CLASS =
  "w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500";

export default function MyKanbanPage() {
  const { token, user } = useAuth();
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [projectFilter, setProjectFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showNewTask, setShowNewTask] = useState(false);
  const [newProjectId, setNewProjectId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newIssueType, setNewIssueType] = useState<IssueType>("task");
  const [newPriority, setNewPriority] = useState<IssuePriority>("medium");
  const [newStartDate, setNewStartDate] = useState("");
  const [newDueDate, setNewDueDate] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    Promise.all([listMyPendingIssues(token), listProjects(token)])
      .then(([issueData, projectData]) => {
        setIssues(issueData);
        setProjects(projectData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load your tasks"))
      .finally(() => setIsLoading(false));
  }, [token]);

  const projectsWithTasks = useMemo(() => {
    const projectIds = new Set(issues.map((issue) => issue.project_id));
    return projects.filter((project) => projectIds.has(project.id));
  }, [issues, projects]);

  const visibleIssues = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return issues.filter(
      (issue) =>
        (!projectFilter || issue.project_id === projectFilter) &&
        (!normalizedSearch || issue.title.toLowerCase().includes(normalizedSearch)),
    );
  }, [issues, projectFilter, search]);

  async function handleMoveIssue(issueId: string, status: IssueStatus) {
    if (!token) return;
    const previous = issues;
    setError(null);
    setIssues((current) =>
      status === "done"
        ? current.filter((issue) => issue.id !== issueId)
        : current.map((issue) => (issue.id === issueId ? { ...issue, status } : issue)),
    );
    try {
      await updateIssueStatus(token, issueId, status);
    } catch (err) {
      setIssues(previous);
      setError(err instanceof Error ? err.message : "Failed to move task");
    }
  }

  function openNewTask() {
    setNewProjectId(projectFilter || projects[0]?.id || "");
    setCreateError(null);
    setShowNewTask(true);
  }

  function closeNewTask() {
    if (isCreating) return;
    setShowNewTask(false);
    setCreateError(null);
  }

  async function handleCreateTask(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !user || !newProjectId || !newTitle.trim()) return;
    if (newStartDate && newDueDate && newDueDate < newStartDate) {
      setCreateError("Due date cannot be before the start date.");
      return;
    }

    setIsCreating(true);
    setCreateError(null);
    try {
      const created = await createIssue(token, newProjectId, {
        title: newTitle.trim(),
        description: newDescription.trim() || null,
        issue_type: newIssueType,
        priority: newPriority,
        assignee_id: user.id,
        start_date: newStartDate || null,
        due_date: newDueDate || null,
      });
      setIssues((current) => [created, ...current]);
      if (projectFilter && projectFilter !== created.project_id) setProjectFilter("");
      setSearch("");
      setNewTitle("");
      setNewDescription("");
      setNewIssueType("task");
      setNewPriority("medium");
      setNewStartDate("");
      setNewDueDate("");
      setShowNewTask(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <AppShell breadcrumb="My Kanban">
      <div className="mx-auto max-w-[96rem] space-y-5 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">My Kanban</h1>
            <p className="mt-1 text-sm text-slate-500">
              {isLoading
                ? "Loading your assigned work..."
                : `${issues.length} pending ${issues.length === 1 ? "task" : "tasks"} across ${projectsWithTasks.length} ${projectsWithTasks.length === 1 ? "project" : "projects"}`}
              {user?.full_name ? ` for ${user.full_name}` : ""}
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={openNewTask}
              disabled={projects.length === 0}
              title={projects.length === 0 ? "Create a project first" : "Create a task for yourself"}
              className="flex items-center justify-center gap-1.5 rounded-lg bg-ember-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-ember-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <PlusIcon className="h-4 w-4" />
              New task
            </button>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Find a task..."
              className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500 sm:w-56"
            />
            <select
              value={projectFilter}
              onChange={(event) => setProjectFilter(event.target.value)}
              className="rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-300 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
            >
              <option value="">All projects</option>
              {projectsWithTasks.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            {[0, 1, 2, 3].map((index) => (
              <div key={index} className="h-80 animate-pulse rounded-lg bg-ink-900" />
            ))}
          </div>
        ) : issues.length === 0 ? (
          <div className="rounded-lg border border-dashed border-ink-700 bg-ink-900/50 px-6 py-16 text-center">
            <h2 className="text-base font-medium text-slate-200">You're all caught up</h2>
            <p className="mt-1 text-sm text-slate-500">
              Tasks assigned to you from any project will appear here.
            </p>
          </div>
        ) : (
          <PersonalKanbanBoard
            issues={visibleIssues}
            projects={projects}
            onMoveIssue={handleMoveIssue}
          />
        )}
      </div>

      {showNewTask && (
        <Modal title="New task" onClose={closeNewTask}>
          <form onSubmit={handleCreateTask} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Project</span>
              <select
                value={newProjectId}
                onChange={(event) => setNewProjectId(event.target.value)}
                required
                autoFocus
                className={INPUT_CLASS}
              >
                <option value="" disabled>
                  Select a project
                </option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Title</span>
              <input
                type="text"
                value={newTitle}
                onChange={(event) => setNewTitle(event.target.value)}
                placeholder="What needs to be done?"
                required
                maxLength={255}
                className={INPUT_CLASS}
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">
                Description <span className="font-normal text-slate-600">(optional)</span>
              </span>
              <textarea
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
                placeholder="Add context or acceptance criteria..."
                rows={3}
                className={INPUT_CLASS}
              />
            </label>

            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Type</span>
                <select
                  value={newIssueType}
                  onChange={(event) => setNewIssueType(event.target.value as IssueType)}
                  className={INPUT_CLASS}
                >
                  <option value="task">Task</option>
                  <option value="bug">Bug</option>
                  <option value="improvement">Improvement</option>
                  <option value="incident">Incident</option>
                </select>
              </label>
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Priority</span>
                <select
                  value={newPriority}
                  onChange={(event) => setNewPriority(event.target.value as IssuePriority)}
                  className={INPUT_CLASS}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Start date</span>
                <input
                  type="date"
                  value={newStartDate}
                  onChange={(event) => setNewStartDate(event.target.value)}
                  className={INPUT_CLASS}
                />
              </label>
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Due date</span>
                <input
                  type="date"
                  value={newDueDate}
                  min={newStartDate || undefined}
                  onChange={(event) => setNewDueDate(event.target.value)}
                  className={INPUT_CLASS}
                />
              </label>
            </div>

            <p className="text-xs text-slate-500">
              This task will be assigned to you automatically.
            </p>
            {createError && <p className="text-sm text-red-400">{createError}</p>}

            <ModalActions>
              <button
                type="button"
                onClick={closeNewTask}
                disabled={isCreating}
                className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreating || !newProjectId || !newTitle.trim()}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isCreating ? "Creating..." : "Create task"}
              </button>
            </ModalActions>
          </form>
        </Modal>
      )}
    </AppShell>
  );
}
