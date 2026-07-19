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
  created_by: string;
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

export interface AreaTypeResponse {
  id: string;
  name: string;
  description: string | null;
}

export interface AreaStatusResponse {
  id: string;
  area_type_id: string;
  name: string;
  sort_order: number;
}

export interface ProjectAreaResponse {
  id: string;
  project_id: string;
  area_type: AreaTypeResponse;
  status: AreaStatusResponse;
  updated_by: string | null;
  updated_at: string;
}

export type ImplementationStatus = "planned" | "active" | "superseded" | "decommissioned";

export interface PlantResponse {
  id: string;
  project_id: string;
  name: string;
  location: string | null;
  created_at: string;
}

export interface MachineResponse {
  id: string;
  plant_id: string;
  name: string;
  machine_type: string | null;
  location: string | null;
  created_at: string;
}

export interface ImplementationResponse {
  id: string;
  machine_id: string;
  label: string;
  status: ImplementationStatus;
  superseded_by: string | null;
  created_at: string;
}

export interface AuditLogEntryResponse {
  id: string;
  project_id: string;
  actor_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  diff: Record<string, unknown>;
  occurred_at: string;
}

export interface ActivityEntryResponse {
  id: string;
  project_id: string;
  project_name: string;
  actor_id: string;
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
  return response.json() as Promise<T>;
}

async function authFetch<T>(
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

export function listProjectAreas(
  token: string,
  projectId: string,
): Promise<ProjectAreaResponse[]> {
  return authFetch(token, `/projects/${projectId}/areas`);
}

export function listAreaStatuses(
  token: string,
  areaTypeId: string,
): Promise<AreaStatusResponse[]> {
  return authFetch(token, `/catalog/area-types/${areaTypeId}/statuses`);
}

export function updateProjectAreaStatus(
  token: string,
  projectId: string,
  areaId: string,
  statusId: string,
): Promise<ProjectAreaResponse> {
  return authFetch(token, `/projects/${projectId}/areas/${areaId}`, {
    method: "PATCH",
    body: JSON.stringify({ status_id: statusId }),
  });
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

export function listProjectPlants(token: string, projectId: string): Promise<PlantResponse[]> {
  return authFetch(token, `/projects/${projectId}/plants`);
}

export function createPlant(
  token: string,
  projectId: string,
  name: string,
  location: string,
): Promise<PlantResponse> {
  return authFetch(token, `/projects/${projectId}/plants`, {
    method: "POST",
    body: JSON.stringify({ name, location: location || null }),
  });
}

export function listPlantMachines(token: string, plantId: string): Promise<MachineResponse[]> {
  return authFetch(token, `/plants/${plantId}/machines`);
}

export function createMachine(
  token: string,
  plantId: string,
  name: string,
  machineType: string,
  location: string,
): Promise<MachineResponse> {
  return authFetch(token, `/plants/${plantId}/machines`, {
    method: "POST",
    body: JSON.stringify({
      name,
      machine_type: machineType || null,
      location: location || null,
    }),
  });
}

export function listMachineImplementations(
  token: string,
  machineId: string,
): Promise<ImplementationResponse[]> {
  return authFetch(token, `/machines/${machineId}/implementations`);
}

export function createImplementation(
  token: string,
  machineId: string,
  label: string,
  status: ImplementationStatus,
): Promise<ImplementationResponse> {
  return authFetch(token, `/machines/${machineId}/implementations`, {
    method: "POST",
    body: JSON.stringify({ label, status }),
  });
}
