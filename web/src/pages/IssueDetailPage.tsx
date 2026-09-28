import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  attachIssueLabel,
  createIssueComment,
  detachIssueLabel,
  getIssue,
  getIssueHistory,
  listIssueComments,
  listProjectIssues,
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
import type { AuditLogEntryResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import {
  LabelChip,
  PriorityBadge,
  PriorityScoreChip,
  ScheduleStatusBadge,
  StatusBadge,
  UrgencyBadge,
} from "../components/IssueBadges";
import Modal, { ModalActions } from "../components/Modal";
import ProjectTabs from "../components/ProjectTabs";

const STATUS_OPTIONS: IssueStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];

export default function IssueDetailPage() {
  const { projectId, issueId } = useParams<{ projectId: string; issueId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [issue, setIssue] = useState<IssueResponse | null>(null);
  const [labels, setLabels] = useState<LabelResponse[]>([]);
  const [comments, setComments] = useState<IssueCommentResponse[]>([]);
  const [history, setHistory] = useState<AuditLogEntryResponse[]>([]);
  const [projectIssues, setProjectIssues] = useState<IssueResponse[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<IssuePriority>("medium");
  const [issueType, setIssueType] = useState<IssueType>("task");
  const [parentIssueId, setParentIssueId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [closedAt, setClosedAt] = useState("");
  const [labelToAdd, setLabelToAdd] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [pendingStatus, setPendingStatus] = useState<IssueStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId && issueId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, issueId]);

  async function loadAll() {
    if (!token || !projectId || !issueId) return;
    try {
      const [projectData, issueData, labelData, commentData, historyData, issuesData] =
        await Promise.all([
          getProject(token, projectId),
          getIssue(token, issueId),
          listProjectLabels(token, projectId),
          listIssueComments(token, issueId),
          getIssueHistory(token, issueId),
          listProjectIssues(token, projectId),
        ]);
      setProject(projectData);
      setIssue(issueData);
      setLabels(labelData);
      setComments(commentData);
      setHistory(historyData);
      setProjectIssues(issuesData);
      setTitle(issueData.title);
      setDescription(issueData.description ?? "");
      setPriority(issueData.priority);
      setIssueType(issueData.issue_type);
      setParentIssueId(issueData.parent_issue_id ?? "");
      setStartDate(issueData.start_date ?? "");
      setDueDate(issueData.due_date ?? "");
      setClosedAt(issueData.closed_at_date ?? "");
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
        assignee_id: issue.assignee_id,
        parent_issue_id: parentIssueId || null,
        start_date: startDate || null,
        due_date: dueDate || null,
        closed_at: closedAt || null,
      });
      setIssue(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save issue");
    }
  }

  function handleStatusChange(status: IssueStatus) {
    if (status === "done") {
      setPendingStatus(status);
      return;
    }
    void applyStatusChange(status);
  }

  async function applyStatusChange(status: IssueStatus) {
    if (!token || !issue) return;
    try {
      const updated = await updateIssueStatus(token, issue.id, status);
      setIssue(updated);
      setClosedAt(updated.closed_at_date ?? "");
      setHistory(await getIssueHistory(token, issue.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleConfirmDone() {
    if (!pendingStatus) return;
    await applyStatusChange(pendingStatus);
    setPendingStatus(null);
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
  const availableParents = projectIssues.filter((candidate) => candidate.id !== issue.id);
  const parentIssue = projectIssues.find((candidate) => candidate.id === issue.parent_issue_id);

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-3xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        {parentIssue && (
          <p className="text-xs text-slate-500">
            Subtask of{" "}
            <Link
              to={`/projects/${projectId}/issues/${parentIssue.id}`}
              className="text-ember-400 hover:text-ember-300"
            >
              {parentIssue.title}
            </Link>
          </p>
        )}

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

          <div className="border-t border-ink-800 pt-3">
            <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">Schedule</h3>
            <div className="flex flex-wrap items-end gap-2">
              <label className="flex flex-col gap-1 text-xs text-slate-500">
                Parent task
                <select
                  value={parentIssueId}
                  onChange={(e) => setParentIssueId(e.target.value)}
                  className="w-48 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
                >
                  <option value="">None</option>
                  {availableParents.map((candidate) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-500">
                Start date
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-500">
                Due date
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-500">
                Closed date
                <input
                  type="date"
                  value={closedAt}
                  onChange={(e) => setClosedAt(e.target.value)}
                  title="Manually correct the close date - set automatically when status moves to Done, but editable here for backfilling."
                  className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
                />
              </label>
              {issue.days_planned !== null && (
                <span className="pb-1.5 text-xs text-slate-500">
                  {issue.days_planned}d planned
                </span>
              )}
              <button
                onClick={handleSave}
                className="rounded-md border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:border-ink-600"
              >
                Save schedule
              </button>
            </div>
            {(issue.urgency || issue.priority_score !== null || issue.schedule_status) && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {issue.urgency && <UrgencyBadge urgency={issue.urgency} />}
                {issue.priority_score !== null && (
                  <PriorityScoreChip score={issue.priority_score} />
                )}
                {issue.schedule_status && <ScheduleStatusBadge status={issue.schedule_status} />}
                {issue.days_taken !== null && (
                  <span className="text-xs text-slate-500">{issue.days_taken}d taken</span>
                )}
              </div>
            )}
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

        <section className="rounded-md border border-ink-800 bg-ink-900 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-100">History</h2>
          {history.length === 0 ? (
            <p className="text-sm text-slate-500">No changes recorded yet.</p>
          ) : (
            <ul className="space-y-2 border-l border-ink-700 pl-4">
              {history.map((entry) => (
                <li key={entry.id} className="relative text-sm">
                  <span className="absolute -left-[1.1rem] top-1.5 h-2 w-2 rounded-full bg-ember-500" />
                  <span className="text-slate-200">
                    {entry.action === "issue.status_changed"
                      ? `Status changed: ${String(entry.diff.from)} → ${String(entry.diff.to)}`
                      : entry.action}
                  </span>
                  <span className="ml-2 text-xs text-slate-500">
                    {new Date(entry.occurred_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {pendingStatus && (
        <Modal title="Close this activity?" onClose={() => setPendingStatus(null)}>
          <p className="text-sm text-slate-400">
            Marking <span className="text-slate-200">{issue.title}</span> as done will record the
            close date and remove it from open Kanban columns. This can be reopened later by
            changing its status again.
          </p>
          <ModalActions>
            <button
              onClick={() => setPendingStatus(null)}
              className="rounded-md border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmDone}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Close activity
            </button>
          </ModalActions>
        </Modal>
      )}
    </AppShell>
  );
}
