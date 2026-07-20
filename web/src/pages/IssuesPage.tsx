import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  createIssue,
  listProjectIssues,
  listProjectLabels,
  listProjectMilestones,
  type IssuePriority,
  type IssueResponse,
  type IssueStatus,
  type IssueType,
  type LabelResponse,
  type MilestoneProgressResponse,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { LabelChip, PriorityBadge, StatusBadge } from "../components/IssueBadges";
import ProjectTabs from "../components/ProjectTabs";

const STATUS_OPTIONS: IssueStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];

export default function IssuesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [labels, setLabels] = useState<LabelResponse[]>([]);
  const [milestones, setMilestones] = useState<MilestoneProgressResponse[]>([]);
  const [statusFilter, setStatusFilter] = useState<IssueStatus | "">("");
  const [labelFilter, setLabelFilter] = useState("");
  const [milestoneFilter, setMilestoneFilter] = useState("");
  const [showNewIssue, setShowNewIssue] = useState(false);
  const [title, setTitle] = useState("");
  const [issueType, setIssueType] = useState<IssueType>("task");
  const [priority, setPriority] = useState<IssuePriority>("medium");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, statusFilter, labelFilter, milestoneFilter]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, issueData, labelData, milestoneData] = await Promise.all([
        getProject(token, projectId),
        listProjectIssues(token, projectId, {
          status: statusFilter || undefined,
          label_id: labelFilter || undefined,
          milestone_id: milestoneFilter || undefined,
        }),
        listProjectLabels(token, projectId),
        listProjectMilestones(token, projectId),
      ]);
      setProject(projectData);
      setIssues(issueData);
      setLabels(labelData);
      setMilestones(milestoneData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load issues");
    }
  }

  async function handleCreateIssue() {
    if (!token || !projectId || !title.trim()) return;
    try {
      await createIssue(token, projectId, { title, issue_type: issueType, priority });
      setTitle("");
      setIssueType("task");
      setPriority("medium");
      setShowNewIssue(false);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create issue");
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

      <div className="mx-auto max-w-5xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as IssueStatus | "")}
            className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>

          <select
            value={labelFilter}
            onChange={(e) => setLabelFilter(e.target.value)}
            className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
          >
            <option value="">All labels</option>
            {labels.map((label) => (
              <option key={label.id} value={label.id}>
                {label.name}
              </option>
            ))}
          </select>

          <select
            value={milestoneFilter}
            onChange={(e) => setMilestoneFilter(e.target.value)}
            className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
          >
            <option value="">All milestones</option>
            {milestones.map((milestone) => (
              <option key={milestone.id} value={milestone.id}>
                {milestone.title}
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowNewIssue((prev) => !prev)}
            className="ml-auto rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
          >
            New issue
          </button>
        </div>

        {showNewIssue && (
          <div className="space-y-2 rounded-md border border-ink-800 bg-ink-900 p-4">
            <input
              type="text"
              placeholder="Issue title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <div className="flex gap-2">
              <select
                value={issueType}
                onChange={(e) => setIssueType(e.target.value as IssueType)}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              >
                <option value="task">task</option>
                <option value="bug">bug</option>
                <option value="improvement">improvement</option>
                <option value="incident">incident</option>
              </select>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as IssuePriority)}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="urgent">urgent</option>
              </select>
              <button
                onClick={handleCreateIssue}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          </div>
        )}

        <div className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
          {issues.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No issues match these filters.</p>
          ) : (
            issues.map((issue) => (
              <Link
                key={issue.id}
                to={`/projects/${projectId}/issues/${issue.id}`}
                className="flex flex-wrap items-center gap-2 p-3 text-sm transition-colors hover:bg-ink-800"
              >
                <StatusBadge status={issue.status} />
                <span className="text-slate-100">{issue.title}</span>
                <PriorityBadge priority={issue.priority} />
                <span className="text-xs text-slate-500">{issue.issue_type}</span>
                {issue.labels.map((label) => (
                  <LabelChip key={label.id} label={label} />
                ))}
              </Link>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
