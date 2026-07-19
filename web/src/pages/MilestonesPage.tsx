import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  createMilestone,
  listProjectMilestones,
  updateMilestoneStatus,
  type MilestoneProgressResponse,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import ProjectTabs from "../components/ProjectTabs";

export default function MilestonesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [milestones, setMilestones] = useState<MilestoneProgressResponse[]>([]);
  const [showNewMilestone, setShowNewMilestone] = useState(false);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, milestoneData] = await Promise.all([
        getProject(token, projectId),
        listProjectMilestones(token, projectId),
      ]);
      setProject(projectData);
      setMilestones(milestoneData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load milestones");
    }
  }

  async function handleCreateMilestone() {
    if (!token || !projectId || !title.trim()) return;
    try {
      await createMilestone(token, projectId, title, "", dueDate);
      setTitle("");
      setDueDate("");
      setShowNewMilestone(false);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create milestone");
    }
  }

  async function handleToggleStatus(milestone: MilestoneProgressResponse) {
    if (!token) return;
    try {
      await updateMilestoneStatus(
        token,
        milestone.id,
        milestone.status === "open" ? "closed" : "open",
      );
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update milestone");
    }
  }

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-3xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100">Milestones</h2>
          <button
            onClick={() => setShowNewMilestone((prev) => !prev)}
            className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
          >
            New milestone
          </button>
        </div>

        {showNewMilestone && (
          <div className="space-y-2 rounded-md border border-ink-800 bg-ink-900 p-4">
            <input
              type="text"
              placeholder="Milestone title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <div className="flex gap-2">
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateMilestone}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {milestones.length === 0 ? (
            <p className="text-sm text-slate-500">No milestones yet.</p>
          ) : (
            milestones.map((milestone) => (
              <div
                key={milestone.id}
                className="rounded-md border border-ink-800 bg-ink-900 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-100">{milestone.title}</span>
                  <button
                    onClick={() => handleToggleStatus(milestone)}
                    className="text-xs text-slate-400 transition-colors hover:text-ember-400"
                  >
                    {milestone.status === "open" ? "Close" : "Reopen"}
                  </button>
                </div>
                {milestone.due_date && (
                  <p className="mt-1 text-xs text-slate-500">Due {milestone.due_date}</p>
                )}
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-800">
                  <div
                    className="h-full bg-ember-500"
                    style={{ width: `${milestone.percent_complete}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {milestone.closed_issues}/{milestone.total_issues} issues closed (
                  {milestone.percent_complete}%)
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
