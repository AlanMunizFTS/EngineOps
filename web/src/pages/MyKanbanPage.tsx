import { useEffect, useMemo, useState } from "react";

import { listProjects, type ProjectResponse } from "../api/client";
import {
  listMyPendingIssues,
  updateIssueStatus,
  type IssueResponse,
  type IssueStatus,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import PersonalKanbanBoard from "../components/PersonalKanbanBoard";

export default function MyKanbanPage() {
  const { token, user } = useAuth();
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [projectFilter, setProjectFilter] = useState("");
  const [search, setSearch] = useState("");
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
    </AppShell>
  );
}
