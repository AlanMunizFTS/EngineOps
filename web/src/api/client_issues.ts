// Phase 2 API client: labels, issues, comments, kanban - split out from
// client.ts to keep that module under the ~400-line limit.

import { authFetch, type AuditLogEntryResponse } from "./client";

export interface LabelResponse {
  id: string;
  project_id: string;
  name: string;
  color: string;
}

export type IssueStatus = "backlog" | "todo" | "in_progress" | "in_review" | "done";
export type IssuePriority = "low" | "medium" | "high" | "urgent";
export type IssueType = "bug" | "task" | "improvement" | "incident";
export type Urgency = "low" | "medium" | "high";
export type ScheduleStatus = "closed" | "on_time" | "late";

export interface KanbanColumnResponse {
  id: string;
  board_id: string;
  name: string;
  order_index: number;
  maps_to_statuses: IssueStatus[];
}

export interface KanbanBoardResponse {
  id: string;
  project_id: string;
  name: string;
  columns: KanbanColumnResponse[];
}

export interface IssueResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: IssueStatus;
  priority: IssuePriority;
  issue_type: IssueType;
  assignee_id: string | null;
  created_by: string | null;
  created_at: string;
  closed_at: string | null;
  closed_at_date: string | null;
  parent_issue_id: string | null;
  parent_assigned_at: string | null;
  start_date: string | null;
  due_date: string | null;
  days_planned: number | null;
  days_taken: number | null;
  urgency: Urgency | null;
  priority_score: number | null;
  schedule_status: ScheduleStatus | null;
  labels: LabelResponse[];
}

export interface IssueCommentResponse {
  id: string;
  issue_id: string;
  author_id: string | null;
  body: string;
  created_at: string;
  edited_at: string | null;
}

export interface IssueFilters {
  status?: IssueStatus;
  assignee_id?: string;
  label_id?: string;
}

export function listProjectLabels(token: string, projectId: string): Promise<LabelResponse[]> {
  return authFetch(token, `/projects/${projectId}/labels`);
}

export function createLabel(
  token: string,
  projectId: string,
  name: string,
  color: string,
): Promise<LabelResponse> {
  return authFetch(token, `/projects/${projectId}/labels`, {
    method: "POST",
    body: JSON.stringify({ name, color }),
  });
}

export function listKanbanBoards(
  token: string,
  projectId: string,
): Promise<KanbanBoardResponse[]> {
  return authFetch(token, `/projects/${projectId}/kanban-boards`);
}

export function createKanbanBoard(
  token: string,
  projectId: string,
  name: string,
): Promise<KanbanBoardResponse> {
  return authFetch(token, `/projects/${projectId}/kanban-boards`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameKanbanBoard(
  token: string,
  boardId: string,
  name: string,
): Promise<KanbanBoardResponse> {
  return authFetch(token, `/kanban-boards/${boardId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteKanbanBoard(token: string, boardId: string): Promise<void> {
  return authFetch(token, `/kanban-boards/${boardId}`, { method: "DELETE" });
}

export function createKanbanColumn(
  token: string,
  boardId: string,
  name: string,
  mapsToStatuses: IssueStatus[],
): Promise<KanbanColumnResponse> {
  return authFetch(token, `/kanban-boards/${boardId}/columns`, {
    method: "POST",
    body: JSON.stringify({ name, maps_to_statuses: mapsToStatuses }),
  });
}

export function updateKanbanColumn(
  token: string,
  columnId: string,
  name: string,
  mapsToStatuses: IssueStatus[],
): Promise<KanbanColumnResponse> {
  return authFetch(token, `/kanban-columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ name, maps_to_statuses: mapsToStatuses }),
  });
}

export function deleteKanbanColumn(token: string, columnId: string): Promise<void> {
  return authFetch(token, `/kanban-columns/${columnId}`, { method: "DELETE" });
}

export function reorderKanbanColumns(
  token: string,
  boardId: string,
  orderedColumnIds: string[],
): Promise<KanbanBoardResponse> {
  return authFetch(token, `/kanban-boards/${boardId}/columns/reorder`, {
    method: "PATCH",
    body: JSON.stringify({ ordered_column_ids: orderedColumnIds }),
  });
}

export function listProjectIssues(
  token: string,
  projectId: string,
  filters: IssueFilters = {},
): Promise<IssueResponse[]> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.assignee_id) params.set("assignee_id", filters.assignee_id);
  if (filters.label_id) params.set("label_id", filters.label_id);
  const query = params.toString();
  return authFetch(token, `/projects/${projectId}/issues${query ? `?${query}` : ""}`);
}

export interface IssueCreateFields {
  title: string;
  description?: string | null;
  issue_type?: IssueType;
  priority?: IssuePriority;
  assignee_id?: string | null;
  parent_issue_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
}

export function createIssue(
  token: string,
  projectId: string,
  fields: IssueCreateFields,
): Promise<IssueResponse> {
  return authFetch(token, `/projects/${projectId}/issues`, {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function getIssue(token: string, issueId: string): Promise<IssueResponse> {
  return authFetch(token, `/issues/${issueId}`);
}

export function getIssueHistory(
  token: string,
  issueId: string,
): Promise<AuditLogEntryResponse[]> {
  return authFetch(token, `/issues/${issueId}/history`);
}

export interface IssueUpdateFields {
  title: string;
  description?: string | null;
  issue_type: IssueType;
  priority: IssuePriority;
  assignee_id?: string | null;
  parent_issue_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  closed_at?: string | null;
}

export function updateIssue(
  token: string,
  issueId: string,
  fields: IssueUpdateFields,
): Promise<IssueResponse> {
  return authFetch(token, `/issues/${issueId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function updateIssueStatus(
  token: string,
  issueId: string,
  status: IssueStatus,
): Promise<IssueResponse> {
  return authFetch(token, `/issues/${issueId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function deleteIssue(token: string, issueId: string): Promise<void> {
  return authFetch(token, `/issues/${issueId}`, { method: "DELETE" });
}

export function attachIssueLabel(
  token: string,
  issueId: string,
  labelId: string,
): Promise<IssueResponse> {
  return authFetch(token, `/issues/${issueId}/labels`, {
    method: "POST",
    body: JSON.stringify({ label_id: labelId }),
  });
}

export function detachIssueLabel(
  token: string,
  issueId: string,
  labelId: string,
): Promise<IssueResponse> {
  return authFetch(token, `/issues/${issueId}/labels/${labelId}`, { method: "DELETE" });
}

export function listIssueComments(
  token: string,
  issueId: string,
): Promise<IssueCommentResponse[]> {
  return authFetch(token, `/issues/${issueId}/comments`);
}

export function createIssueComment(
  token: string,
  issueId: string,
  body: string,
): Promise<IssueCommentResponse> {
  return authFetch(token, `/issues/${issueId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function updateIssueComment(
  token: string,
  commentId: string,
  body: string,
): Promise<IssueCommentResponse> {
  return authFetch(token, `/issue-comments/${commentId}`, {
    method: "PATCH",
    body: JSON.stringify({ body }),
  });
}
