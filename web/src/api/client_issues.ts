// Phase 2 API client: labels, milestones, issues, comments, kanban - split
// out from client.ts to keep that module under the ~400-line limit.

import { authFetch } from "./client";

export interface LabelResponse {
  id: string;
  project_id: string;
  name: string;
  color: string;
}

export type MilestoneStatus = "open" | "closed";

export interface MilestoneResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: MilestoneStatus;
  created_at: string;
}

export interface MilestoneProgressResponse extends MilestoneResponse {
  total_issues: number;
  closed_issues: number;
  percent_complete: number;
}

export type IssueStatus = "backlog" | "todo" | "in_progress" | "in_review" | "done";
export type IssuePriority = "low" | "medium" | "high" | "urgent";
export type IssueType = "bug" | "task" | "improvement" | "incident";

export interface KanbanColumnResponse {
  id: string;
  board_id: string;
  name: string;
  order_index: number;
  maps_to_status: IssueStatus;
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
  plant_id: string | null;
  machine_id: string | null;
  implementation_id: string | null;
  title: string;
  description: string | null;
  status: IssueStatus;
  priority: IssuePriority;
  issue_type: IssueType;
  milestone_id: string | null;
  assignee_id: string | null;
  created_by: string;
  created_at: string;
  closed_at: string | null;
  labels: LabelResponse[];
}

export interface IssueCommentResponse {
  id: string;
  issue_id: string;
  author_id: string;
  body: string;
  created_at: string;
  edited_at: string | null;
}

export interface IssueHierarchyLink {
  plant_id?: string | null;
  machine_id?: string | null;
  implementation_id?: string | null;
}

export interface IssueFilters {
  status?: IssueStatus;
  assignee_id?: string;
  label_id?: string;
  milestone_id?: string;
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

export function listProjectMilestones(
  token: string,
  projectId: string,
): Promise<MilestoneProgressResponse[]> {
  return authFetch(token, `/projects/${projectId}/milestones`);
}

export function createMilestone(
  token: string,
  projectId: string,
  title: string,
  description: string,
  dueDate: string,
): Promise<MilestoneResponse> {
  return authFetch(token, `/projects/${projectId}/milestones`, {
    method: "POST",
    body: JSON.stringify({
      title,
      description: description || null,
      due_date: dueDate || null,
    }),
  });
}

export function updateMilestoneStatus(
  token: string,
  milestoneId: string,
  status: MilestoneStatus,
): Promise<MilestoneResponse> {
  return authFetch(token, `/milestones/${milestoneId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function getProjectKanbanBoard(
  token: string,
  projectId: string,
): Promise<KanbanBoardResponse> {
  return authFetch(token, `/projects/${projectId}/kanban`);
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
  if (filters.milestone_id) params.set("milestone_id", filters.milestone_id);
  const query = params.toString();
  return authFetch(token, `/projects/${projectId}/issues${query ? `?${query}` : ""}`);
}

export interface IssueCreateFields extends IssueHierarchyLink {
  title: string;
  description?: string | null;
  issue_type?: IssueType;
  priority?: IssuePriority;
  milestone_id?: string | null;
  assignee_id?: string | null;
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

export interface IssueUpdateFields extends IssueHierarchyLink {
  title: string;
  description?: string | null;
  issue_type: IssueType;
  priority: IssuePriority;
  milestone_id?: string | null;
  assignee_id?: string | null;
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
