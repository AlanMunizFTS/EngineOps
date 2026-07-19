import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  attachIssueLabel,
  createIssueComment,
  detachIssueLabel,
  getIssue,
  listIssueComments,
  listProjectLabels,
  updateIssue,
  updateIssueStatus,
  type IssueCommentResponse,
  type IssuePriority,
  type IssueResponse,
  type IssueStatus,
  type IssueType,
  type LabelResponse,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { LabelChip, PriorityBadge, StatusBadge } from "../components/IssueBadges";
import ProjectTabs from "../components/ProjectTabs";

const STATUS_OPTIONS: IssueStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];

export default function IssueDetailPage() {
  const { projectId, issueId } = useParams<{ projectId: string; issueId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [issue, setIssue] = useState<IssueResponse | null>(null);
  const [labels, setLabels] = useState<LabelResponse[]>([]);
  const [comments, setComments] = useState<IssueCommentResponse[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<IssuePriority>("medium");
  const [issueType, setIssueType] = useState<IssueType>("task");
  const [labelToAdd, setLabelToAdd] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId && issueId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, issueId]);

  async function loadAll() {
    if (!token || !projectId || !issueId) return;
    try {
      const [projectData, issueData, labelData, commentData] = await Promise.all([
        getProject(token, projectId),
        getIssue(token, issueId),
        listProjectLabels(token, projectId),
        listIssueComments(token, issueId),
      ]);
      setProject(projectData);
      setIssue(issueData);
      setLabels(labelData);
      setComments(commentData);
      setTitle(issueData.title);
      setDescription(issueData.description ?? "");
      setPriority(issueData.priority);
      setIssueType(issueData.issue_type);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load issue");
    }
  }

  async function handleSave() {
    if (!token || !issue) return;
    try {
      const updated = await updateIssue(token, issue.id, {
        title,
        description: description || null,
        priority,
        issue_type: issueType,
        milestone_id: issue.milestone_id,
        assignee_id: issue.assignee_id,
      });
      setIssue(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save issue");
    }
  }

  async function handleStatusChange(status: IssueStatus) {
    if (!token || !issue) return;
    try {
      setIssue(await updateIssueStatus(token, issue.id, status));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleAddLabel() {
    if (!token || !issue || !labelToAdd) return;
    try {
      setIssue(await attachIssueLabel(token, issue.id, labelToAdd));
      setLabelToAdd("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to attach label");
    }
  }

  async function handleRemoveLabel(labelId: string) {
    if (!token || !issue) return;
    try {
      setIssue(await detachIssueLabel(token, issue.id, labelId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove label");
    }
  }

  async function handleAddComment() {
    if (!token || !issue || !commentBody.trim()) return;
    try {
      const comment = await createIssueComment(token, issue.id, commentBody);
      setComments((current) => [...current, comment]);
      setCommentBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add comment");
    }
  }

  if (!project || !issue) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  const availableLabels = labels.filter(
    (label) => !issue.labels.some((attached) => attached.id === label.id),
  );

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-3xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="space-y-2 rounded-md border border-ink-800 bg-ink-900 p-4">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm font-medium text-slate-100 outline-none focus:border-ember-500"
          />
          <textarea
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
          />
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={issue.status}
              onChange={(e) => handleStatusChange(e.target.value as IssueStatus)}
              className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
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
              onClick={handleSave}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Save
            </button>
            <StatusBadge status={issue.status} />
            <PriorityBadge priority={issue.priority} />
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-2">
            {issue.labels.map((label) => (
              <button key={label.id} onClick={() => handleRemoveLabel(label.id)}>
                <LabelChip label={label} />
              </button>
            ))}
            {availableLabels.length > 0 && (
              <div className="flex items-center gap-1">
                <select
                  value={labelToAdd}
                  onChange={(e) => setLabelToAdd(e.target.value)}
                  className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-xs text-slate-200 outline-none focus:border-ember-500"
                >
                  <option value="">Add label...</option>
                  {availableLabels.map((label) => (
                    <option key={label.id} value={label.id}>
                      {label.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleAddLabel}
                  className="text-xs text-slate-400 hover:text-ember-400"
                >
                  Add
                </button>
              </div>
            )}
          </div>
        </div>

        <section className="rounded-md border border-ink-800 bg-ink-900 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-100">Comments</h2>
          <div className="space-y-3">
            {comments.length === 0 ? (
              <p className="text-sm text-slate-500">No comments yet.</p>
            ) : (
              comments.map((comment) => (
                <div key={comment.id} className="rounded-md bg-ink-800 p-2 text-sm">
                  <p className="text-slate-200">{comment.body}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {new Date(comment.created_at).toLocaleString()}
                    {comment.edited_at ? " (edited)" : ""}
                  </p>
                </div>
              ))
            )}
          </div>
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              placeholder="Add a comment..."
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              className="flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <button
              onClick={handleAddComment}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Comment
            </button>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
