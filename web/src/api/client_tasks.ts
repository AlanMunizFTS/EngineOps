// Tasks, milestones, labels, comments, and kanban API client.
// client.ts to keep that module under the ~400-line limit.

import { authFetch, type AuditLogEntryResponse } from "./client";

export interface LabelResponse {
  id: string;
  project_id: string;
  name: string;
  color: string;
}

export type TaskStatus = "backlog" | "todo" | "in_progress" | "in_review" | "done";
export type TaskPriority = "low" | "medium" | "high" | "urgent";
export type TaskType = "bug" | "task" | "improvement" | "incident";
export type MilestoneStatus = "open" | "closed";
export type Urgency = "low" | "medium" | "high";
export type ScheduleStatus = "closed" | "on_time" | "late";

export interface KanbanColumnResponse {
  id: string;
  board_id: string;
  name: string;
  order_index: number;
  maps_to_statuses: TaskStatus[];
}

export interface KanbanBoardResponse {
  id: string;
  project_id: string;
  name: string;
  columns: KanbanColumnResponse[];
}

export interface TaskResponse {
  id: string;
  project_id: string;
  milestone_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  task_type: TaskType;
  assignee_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  closed_at_date: string | null;
  parent_task_id: string | null;
  parent_assigned_at: string | null;
  start_date: string | null;
  due_date: string | null;
  days_planned: number | null;
  days_taken: number | null;
  urgency: Urgency | null;
  priority_score: number | null;
  schedule_status: ScheduleStatus | null;
  labels: LabelResponse[];
  subtasks_total: number;
  subtasks_completed: number;
}

export interface TaskCommentResponse {
  id: string;
  task_id: string;
  author_id: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface MilestoneResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: MilestoneStatus;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  total_tasks: number;
  completed_tasks: number;
  progress_percentage: number;
}

export interface TaskFilters {
  status?: TaskStatus;
  priority?: TaskPriority;
  task_type?: TaskType;
  assignee_id?: string;
  milestone_id?: string;
  label_id?: string;
  include_subtasks?: boolean;
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
  mapsToStatuses: TaskStatus[],
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
  mapsToStatuses: TaskStatus[],
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

export function listProjectTasks(
  token: string,
  projectId: string,
  filters: TaskFilters = {},
): Promise<TaskResponse[]> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.task_type) params.set("task_type", filters.task_type);
  if (filters.assignee_id) params.set("assignee_id", filters.assignee_id);
  if (filters.milestone_id) params.set("milestone_id", filters.milestone_id);
  if (filters.label_id) params.set("label_id", filters.label_id);
  if (filters.include_subtasks) params.set("include_subtasks", "true");
  const query = params.toString();
  return authFetch(token, `/projects/${projectId}/tasks${query ? `?${query}` : ""}`);
}

export function listMyPendingTasks(token: string): Promise<TaskResponse[]> {
  return authFetch(token, "/tasks/assigned-to-me");
}

export interface TaskCreateFields {
  title: string;
  description?: string | null;
  task_type?: TaskType;
  priority?: TaskPriority;
  status?: TaskStatus;
  milestone_id?: string | null;
  assignee_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
}

export async function createTask(
  token: string,
  projectId: string,
  fields: TaskCreateFields,
): Promise<TaskResponse> {
  const { status, ...createFields } = fields;
  const created = await authFetch<TaskResponse>(token, `/projects/${projectId}/tasks`, {
    method: "POST",
    body: JSON.stringify(createFields),
  });
  return status && status !== "backlog" ? updateTaskStatus(token, created.id, status) : created;
}

export function getTask(token: string, taskId: string): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}`);
}

export function getTaskHistory(
  token: string,
  taskId: string,
): Promise<AuditLogEntryResponse[]> {
  return authFetch(token, `/tasks/${taskId}/history`);
}

export interface TaskUpdateFields {
  title?: string;
  description?: string | null;
  task_type?: TaskType;
  priority?: TaskPriority;
  milestone_id?: string | null;
  assignee_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  closed_at?: string | null;
}

export function updateTask(
  token: string,
  taskId: string,
  fields: TaskUpdateFields,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function updateTaskStatus(
  token: string,
  taskId: string,
  status: TaskStatus,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function deleteTask(token: string, taskId: string): Promise<void> {
  return authFetch(token, `/tasks/${taskId}`, { method: "DELETE" });
}

export function attachTaskLabel(
  token: string,
  taskId: string,
  labelId: string,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}/labels/${labelId}`, {
    method: "POST",
  });
}

export function detachTaskLabel(
  token: string,
  taskId: string,
  labelId: string,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}/labels/${labelId}`, { method: "DELETE" });
}

export function listTaskComments(
  token: string,
  taskId: string,
): Promise<TaskCommentResponse[]> {
  return authFetch(token, `/tasks/${taskId}/comments`);
}

export function createTaskComment(
  token: string,
  taskId: string,
  body: string,
): Promise<TaskCommentResponse> {
  return authFetch(token, `/tasks/${taskId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function updateTaskComment(
  token: string,
  commentId: string,
  body: string,
): Promise<TaskCommentResponse> {
  return authFetch(token, `/task-comments/${commentId}`, {
    method: "PATCH",
    body: JSON.stringify({ body }),
  });
}

export function listSubtasks(token: string, taskId: string): Promise<TaskResponse[]> {
  return authFetch(token, `/tasks/${taskId}/subtasks`);
}

export function createSubtask(
  token: string,
  taskId: string,
  fields: TaskCreateFields,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}/subtasks`, {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function updateTaskParent(
  token: string,
  taskId: string,
  parentTaskId: string | null,
): Promise<TaskResponse> {
  return authFetch(token, `/tasks/${taskId}/parent`, {
    method: "PATCH",
    body: JSON.stringify({ parent_task_id: parentTaskId }),
  });
}

export interface MilestoneFields {
  title?: string;
  description?: string | null;
  status?: MilestoneStatus;
  due_date?: string | null;
}

export function listMilestones(token: string, projectId: string): Promise<MilestoneResponse[]> {
  return authFetch(token, `/projects/${projectId}/milestones`);
}

export function createMilestone(
  token: string,
  projectId: string,
  fields: MilestoneFields,
): Promise<MilestoneResponse> {
  return authFetch(token, `/projects/${projectId}/milestones`, {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function getMilestone(token: string, milestoneId: string): Promise<MilestoneResponse> {
  return authFetch(token, `/milestones/${milestoneId}`);
}

export function updateMilestone(
  token: string,
  milestoneId: string,
  fields: MilestoneFields,
): Promise<MilestoneResponse> {
  return authFetch(token, `/milestones/${milestoneId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function deleteMilestone(token: string, milestoneId: string): Promise<void> {
  return authFetch(token, `/milestones/${milestoneId}`, { method: "DELETE" });
}
