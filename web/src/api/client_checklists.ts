import { authFetch } from "./client";

export interface ChecklistItemResponse {
  id: string;
  checklist_id: string;
  content: string;
  position: number;
}

export interface ProjectChecklistResponse {
  id: string;
  project_id: string;
  name: string;
  items: ChecklistItemResponse[];
}

export interface TaskChecklistItemResponse extends ChecklistItemResponse {
  completed: boolean;
}

export interface TaskChecklistResponse {
  id: string;
  project_id: string;
  name: string;
  items: TaskChecklistItemResponse[];
}

export function listProjectChecklists(token: string, projectId: string) {
  return authFetch<ProjectChecklistResponse[]>(token, `/projects/${projectId}/checklists`);
}

export function createProjectChecklist(token: string, projectId: string, name: string) {
  return authFetch<ProjectChecklistResponse>(token, `/projects/${projectId}/checklists`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameProjectChecklist(token: string, checklistId: string, name: string) {
  return authFetch<ProjectChecklistResponse>(token, `/checklists/${checklistId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteProjectChecklist(token: string, checklistId: string): Promise<void> {
  return authFetch(token, `/checklists/${checklistId}`, { method: "DELETE" });
}

export function addProjectChecklistItem(token: string, checklistId: string, content: string) {
  return authFetch<ChecklistItemResponse>(token, `/checklists/${checklistId}/items`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function updateProjectChecklistItem(token: string, itemId: string, content: string) {
  return authFetch<ChecklistItemResponse>(token, `/checklist-items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });
}

export function deleteProjectChecklistItem(token: string, itemId: string): Promise<void> {
  return authFetch(token, `/checklist-items/${itemId}`, { method: "DELETE" });
}

export function listTaskChecklists(token: string, taskId: string) {
  return authFetch<TaskChecklistResponse[]>(token, `/tasks/${taskId}/checklists`);
}

export function attachChecklistToTask(token: string, taskId: string, checklistId: string) {
  return authFetch<TaskChecklistResponse>(token, `/tasks/${taskId}/checklists/${checklistId}`, {
    method: "POST",
  });
}

export function detachChecklistFromTask(
  token: string,
  taskId: string,
  checklistId: string,
): Promise<void> {
  return authFetch(token, `/tasks/${taskId}/checklists/${checklistId}`, { method: "DELETE" });
}

export function setTaskChecklistItemCompleted(
  token: string,
  taskId: string,
  itemId: string,
  completed: boolean,
) {
  return authFetch<TaskChecklistResponse>(token, `/tasks/${taskId}/checklist-items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ completed }),
  });
}
