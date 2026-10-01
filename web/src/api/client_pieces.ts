// Material (piece traceability) API client - mirrors client_tasks.ts.

import { authFetch } from "./client";

export type PieceStatus = "ok" | "nok";

export interface PartNumberResponse {
  id: string;
  project_id: string;
  name: string;
}

export interface PieceConditionResponse {
  id: string;
  project_id: string;
  name: string;
}

export interface PieceLocationResponse {
  id: string;
  project_id: string;
  name: string;
}

export interface MeasurementTypeResponse {
  id: string;
  project_id: string;
  name: string;
  unit: string;
  condition_id: string | null;
  part_number_id: string | null;
  status: PieceStatus | null;
}

export interface MeasurementResponse {
  id: string;
  piece_id: string;
  measurement_type_id: string;
  name: string;
  unit: string;
  value: string;
}

export interface PieceResponse {
  id: string;
  project_id: string;
  tracking_number: string;
  part_number_id: string;
  overall_status: PieceStatus;
  location_id: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  conditions: PieceConditionResponse[];
  measurements: MeasurementResponse[];
}

export function listPartNumbers(token: string, projectId: string): Promise<PartNumberResponse[]> {
  return authFetch(token, `/projects/${projectId}/part-numbers`);
}

export function createPartNumber(
  token: string,
  projectId: string,
  name: string,
): Promise<PartNumberResponse> {
  return authFetch(token, `/projects/${projectId}/part-numbers`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listPieceConditions(
  token: string,
  projectId: string,
): Promise<PieceConditionResponse[]> {
  return authFetch(token, `/projects/${projectId}/piece-conditions`);
}

export function createPieceCondition(
  token: string,
  projectId: string,
  name: string,
): Promise<PieceConditionResponse> {
  return authFetch(token, `/projects/${projectId}/piece-conditions`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listPieceLocations(
  token: string,
  projectId: string,
): Promise<PieceLocationResponse[]> {
  return authFetch(token, `/projects/${projectId}/piece-locations`);
}

export function createPieceLocation(
  token: string,
  projectId: string,
  name: string,
): Promise<PieceLocationResponse> {
  return authFetch(token, `/projects/${projectId}/piece-locations`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listMeasurementTypes(
  token: string,
  projectId: string,
): Promise<MeasurementTypeResponse[]> {
  return authFetch(token, `/projects/${projectId}/measurement-types`);
}

export interface MeasurementTypeCreateFields {
  name: string;
  unit: string;
  condition_id?: string | null;
  part_number_id?: string | null;
  status?: PieceStatus | null;
}

export function createMeasurementType(
  token: string,
  projectId: string,
  fields: MeasurementTypeCreateFields,
): Promise<MeasurementTypeResponse> {
  return authFetch(token, `/projects/${projectId}/measurement-types`, {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export function updateMeasurementType(
  token: string,
  measurementTypeId: string,
  fields: MeasurementTypeCreateFields,
): Promise<MeasurementTypeResponse> {
  return authFetch(token, `/measurement-types/${measurementTypeId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function deleteMeasurementType(token: string, measurementTypeId: string): Promise<void> {
  return authFetch(token, `/measurement-types/${measurementTypeId}`, { method: "DELETE" });
}

export interface PieceFilters {
  part_number_id?: string;
  status?: PieceStatus;
  condition_id?: string[];
  location_id?: string;
  measurement_type_id?: string;
  measurement_min?: string;
  measurement_max?: string;
}

export function listProjectPieces(
  token: string,
  projectId: string,
  filters: PieceFilters = {},
): Promise<PieceResponse[]> {
  const params = new URLSearchParams();
  if (filters.part_number_id) params.set("part_number_id", filters.part_number_id);
  if (filters.status) params.set("status", filters.status);
  for (const id of filters.condition_id ?? []) params.append("condition_id", id);
  if (filters.location_id) params.set("location_id", filters.location_id);
  if (filters.measurement_type_id) params.set("measurement_type_id", filters.measurement_type_id);
  if (filters.measurement_min) params.set("measurement_min", filters.measurement_min);
  if (filters.measurement_max) params.set("measurement_max", filters.measurement_max);
  const query = params.toString();
  return authFetch(token, `/projects/${projectId}/pieces${query ? `?${query}` : ""}`);
}

export interface PieceCreateFields {
  part_number_id: string;
  status: PieceStatus;
  condition_ids?: string[];
  location_id?: string | null;
  notes?: string | null;
  quantity?: number;
}

export function createPieces(
  token: string,
  projectId: string,
  fields: PieceCreateFields,
): Promise<PieceResponse[]> {
  return authFetch(token, `/projects/${projectId}/pieces`, {
    method: "POST",
    body: JSON.stringify(fields),
  });
}

export interface PieceUpdateFields {
  status: PieceStatus;
  location_id?: string | null;
  notes?: string | null;
  condition_ids?: string[];
}

export function updatePiece(
  token: string,
  pieceId: string,
  fields: PieceUpdateFields,
): Promise<PieceResponse> {
  return authFetch(token, `/pieces/${pieceId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function setPieceMeasurement(
  token: string,
  pieceId: string,
  measurementTypeId: string,
  value: string,
): Promise<PieceResponse> {
  return authFetch(token, `/pieces/${pieceId}/measurements/${measurementTypeId}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}
