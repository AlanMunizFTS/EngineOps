const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  roles: string[];
}

export type ProjectRole = "owner" | "contributor" | "viewer";

export interface ProjectResponse {
  id: string;
  name: string;
  description: string | null;
  created_by: string | null;
  created_at: string;
}

export interface ProjectMemberResponse {
  project_id: string;
  user_id: string;
  project_role: ProjectRole;
  added_at: string;
}

export interface ProjectMemberDetailResponse extends ProjectMemberResponse {
  email: string;
  full_name: string;
}

export interface UserSummaryResponse {
  id: string;
  email: string;
  full_name: string;
}

export interface AuditLogEntryResponse {
  id: string;
  project_id: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  diff: Record<string, unknown>;
  occurred_at: string;
}

export type FileTreeNodeType = "folder" | "link" | "file";

export interface FileTreeNodeResponse {
  id: string;
  project_id: string;
  parent_id: string | null;
  node_type: FileTreeNodeType;
  name: string;
  url: string | null;
  content: string | null;
  created_by: string | null;
  created_at: string;
}

export interface ActivityEntryResponse {
  id: string;
  project_id: string;
  project_name: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  diff: Record<string, unknown>;
  occurred_at: string;
}

async function parseOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function authFetch<T>(
  token: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  return parseOrThrow<T>(response);
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseOrThrow<TokenResponse>(response);
}

export async function getCurrentUser(token: string): Promise<UserResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseOrThrow<UserResponse>(response);
}

export function listProjects(token: string): Promise<ProjectResponse[]> {
  return authFetch(token, "/projects");
}

export function getProject(token: string, projectId: string): Promise<ProjectResponse> {
  return authFetch(token, `/projects/${projectId}`);
}

export function createProject(
  token: string,
  name: string,
  description: string,
): Promise<ProjectResponse> {
  return authFetch(token, "/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: description || null }),
  });
}

export function listProjectMembers(
  token: string,
  projectId: string,
): Promise<ProjectMemberDetailResponse[]> {
  return authFetch(token, `/projects/${projectId}/members`);
}

export function listMemberCandidates(
  token: string,
  projectId: string,
): Promise<UserSummaryResponse[]> {
  return authFetch(token, `/projects/${projectId}/members/candidates`);
}

export function addProjectMember(
  token: string,
  projectId: string,
  userId: string,
): Promise<ProjectMemberResponse> {
  return authFetch(token, `/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export function removeProjectMember(
  token: string,
  projectId: string,
  userId: string,
): Promise<void> {
  return authFetch(token, `/projects/${projectId}/members/${userId}`, { method: "DELETE" });
}

export function getProjectTimeline(
  token: string,
  projectId: string,
): Promise<AuditLogEntryResponse[]> {
  return authFetch(token, `/projects/${projectId}/timeline`);
}

export function getRecentActivity(token: string, limit = 20): Promise<ActivityEntryResponse[]> {
  return authFetch(token, `/activity?limit=${limit}`);
}

// Binary download, not JSON - can't go through authFetch/parseOrThrow, which
// always calls response.json().
export async function downloadProjectExport(token: string, projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/export.xlsx`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? "Export failed");
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = /filename="?([^"]+)"?/.exec(disposition);
  const filename = filenameMatch?.[1] ?? "export.xlsx";

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function listFileTree(
  token: string,
  projectId: string,
): Promise<FileTreeNodeResponse[]> {
  return authFetch(token, `/projects/${projectId}/tree`);
}

export function createFileTreeFolder(
  token: string,
  projectId: string,
  name: string,
  parentId: string | null,
): Promise<FileTreeNodeResponse> {
  return authFetch(token, `/projects/${projectId}/tree`, {
    method: "POST",
    body: JSON.stringify({ node_type: "folder", name, parent_id: parentId }),
  });
}

export function createFileTreeLink(
  token: string,
  projectId: string,
  name: string,
  url: string,
  parentId: string | null,
): Promise<FileTreeNodeResponse> {
  return authFetch(token, `/projects/${projectId}/tree`, {
    method: "POST",
    body: JSON.stringify({ node_type: "link", name, url, parent_id: parentId }),
  });
}

export function createFileTreeFile(
  token: string,
  projectId: string,
  name: string,
  content: string,
  parentId: string | null,
): Promise<FileTreeNodeResponse> {
  return authFetch(token, `/projects/${projectId}/tree`, {
    method: "POST",
    body: JSON.stringify({ node_type: "file", name, content, parent_id: parentId }),
  });
}

export function updateFileTreeContent(
  token: string,
  projectId: string,
  nodeId: string,
  content: string,
): Promise<FileTreeNodeResponse> {
  return authFetch(token, `/projects/${projectId}/tree/${nodeId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });
}

export function deleteFileTreeNode(
  token: string,
  projectId: string,
  nodeId: string,
): Promise<void> {
  return authFetch(token, `/projects/${projectId}/tree/${nodeId}`, { method: "DELETE" });
}

// Phase 2 (labels, issues, kanban) lives in ./client_issues.ts to keep this
// module under the ~400-line limit.

export interface AdminCreateUserFields {
  email: string;
  password: string;
  full_name: string;
  is_admin?: boolean;
}

export interface AdminUpdateUserFields {
  email: string;
  full_name: string;
  password?: string;
  is_active: boolean;
  roles: string[];
}

export function listAdminUsers(token: string): Promise<UserResponse[]> {
  return authFetch(token, "/admin/users");
}

export function createAdminUser(
  token: string,
  fields: AdminCreateUserFields,
): Promise<UserResponse> {
  return authFetch(token, "/admin/users", {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function createUser(
  token: string,
  fields: Omit<AdminCreateUserFields, "is_admin">,
): Promise<UserResponse> {
  return authFetch(token, "/auth/users", {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function updateAdminUser(
  token: string,
  userId: string,
  fields: AdminUpdateUserFields,
): Promise<UserResponse> {
  return authFetch(token, `/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function deleteAdminUser(token: string, userId: string): Promise<void> {
  return authFetch(token, `/admin/users/${userId}`, { method: "DELETE" });
}
