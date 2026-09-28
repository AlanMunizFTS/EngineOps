import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  listMeasurementTypes,
  listPartNumbers,
  listPieceConditions,
  listPieceLocations,
  listProjectPieces,
  type MeasurementTypeResponse,
  type PartNumberResponse,
  type PieceConditionResponse,
  type PieceLocationResponse,
  type PieceResponse,
} from "../api/client_pieces";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { ConditionChip } from "../components/MaterialBadges";
import MaterialFilterBar, { type MaterialFilterState } from "../components/MaterialFilterBar";
import MaterialNotesCell from "../components/MaterialNotesCell";
import MaterialRegisterForm from "../components/MaterialRegisterForm";
import MaterialStatusCell from "../components/MaterialStatusCell";
import MeasurementTypeModal from "../components/MeasurementTypeModal";
import PieceMeasurementsModal from "../components/PieceMeasurementsModal";
import ProjectTabs from "../components/ProjectTabs";

const EMPTY_FILTERS: MaterialFilterState = {
  partNumberId: "",
  status: "",
  conditionIds: [],
  locationId: "",
  measurementTypeId: "",
  measurementMin: "",
  measurementMax: "",
};

export default function MaterialPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [partNumbers, setPartNumbers] = useState<PartNumberResponse[]>([]);
  const [conditions, setConditions] = useState<PieceConditionResponse[]>([]);
  const [locations, setLocations] = useState<PieceLocationResponse[]>([]);
  const [measurementTypes, setMeasurementTypes] = useState<MeasurementTypeResponse[]>([]);
  const [pieces, setPieces] = useState<PieceResponse[]>([]);
  const [filters, setFilters] = useState<MaterialFilterState>(EMPTY_FILTERS);
  const [error, setError] = useState<string | null>(null);
  const [showMeasurementTypeModal, setShowMeasurementTypeModal] = useState(false);
  const [measurementsPiece, setMeasurementsPiece] = useState<PieceResponse | null>(null);

  useEffect(() => {
    if (token && projectId) void loadCatalogsAndProject();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  useEffect(() => {
    if (token && projectId) void loadPieces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, filters]);

  async function loadCatalogsAndProject() {
    if (!token || !projectId) return;
    try {
      const [projectData, partNumberData, conditionData, locationData, measurementTypeData] =
        await Promise.all([
          getProject(token, projectId),
          listPartNumbers(token, projectId),
          listPieceConditions(token, projectId),
          listPieceLocations(token, projectId),
          listMeasurementTypes(token, projectId),
        ]);
      setProject(projectData);
      setPartNumbers(partNumberData);
      setConditions(conditionData);
      setLocations(locationData);
      setMeasurementTypes(measurementTypeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load material catalogs");
    }
  }

  async function loadPieces() {
    if (!token || !projectId) return;
    try {
      const data = await listProjectPieces(token, projectId, {
        part_number_id: filters.partNumberId || undefined,
        status: filters.status || undefined,
        condition_id: filters.conditionIds.length > 0 ? filters.conditionIds : undefined,
        location_id: filters.locationId || undefined,
        measurement_type_id: filters.measurementTypeId || undefined,
        measurement_min: filters.measurementMin || undefined,
        measurement_max: filters.measurementMax || undefined,
      });
      setPieces(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pieces");
    }
  }

  function handleMeasurementsSaved(updated: PieceResponse) {
    setPieces((current) => current.map((p) => (p.id === updated.id ? updated : p)));
    // A saved value may push the piece out of an active measurement-range
    // filter, so re-fetch to keep the list/counts consistent.
    void loadPieces();
  }

  function handlePieceUpdated(updated: PieceResponse) {
    setPieces((current) => current.map((p) => (p.id === updated.id ? updated : p)));
  }

  const locationNameById = useMemo(
    () => new Map(locations.map((loc) => [loc.id, loc.name])),
    [locations],
  );
  const partNumberNameById = useMemo(
    () => new Map(partNumbers.map((p) => [p.id, p.name])),
    [partNumbers],
  );

  const countsByLocation = useMemo(() => {
    const counts = new Map<string, number>();
    for (const piece of pieces) {
      const name = piece.location_id
        ? (locationNameById.get(piece.location_id) ?? "Unknown")
        : "Unassigned";
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
  }, [pieces, locationNameById]);

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

      <div className="mx-auto max-w-6xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => setShowMeasurementTypeModal(true)}
            className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600"
          >
            Configure measurements
          </button>
        </div>

        <MaterialFilterBar
          partNumbers={partNumbers}
          conditions={conditions}
          locations={locations}
          measurementTypes={measurementTypes}
          filters={filters}
          onChange={setFilters}
          totalCount={pieces.length}
          countsByLocation={countsByLocation}
        />

        {token && (
          <MaterialRegisterForm
            token={token}
            projectId={project.id}
            partNumbers={partNumbers}
            conditions={conditions}
            locations={locations}
            onCatalogsChanged={loadCatalogsAndProject}
            onPiecesCreated={() => void loadPieces()}
            onError={setError}
          />
        )}

        <div className="overflow-x-auto rounded-md border border-ink-800 bg-ink-900">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-3">Tracking #</th>
                <th className="p-3">Part Number</th>
                <th className="p-3">Status</th>
                <th className="p-3">Conditions</th>
                <th className="p-3">Location</th>
                <th className="p-3">Measurements</th>
                <th className="p-3">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800">
              {pieces.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-4 text-sm text-slate-500">
                    No pieces match these filters.
                  </td>
                </tr>
              ) : (
                pieces.map((piece) => (
                  <tr key={piece.id} className="text-slate-200">
                    <td className="p-3 font-mono text-xs">{piece.tracking_number}</td>
                    <td className="p-3">{partNumberNameById.get(piece.part_number_id) ?? "—"}</td>
                    <td className="p-3">
                      {token && (
                        <MaterialStatusCell
                          token={token}
                          piece={piece}
                          onSaved={handlePieceUpdated}
                        />
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {piece.conditions.map((condition) => (
                          <ConditionChip key={condition.id} condition={condition} />
                        ))}
                      </div>
                    </td>
                    <td className="p-3">
                      {piece.location_id ? (locationNameById.get(piece.location_id) ?? "—") : "—"}
                    </td>
                    <td className="p-3">
                      <button
                        type="button"
                        onClick={() => setMeasurementsPiece(piece)}
                        title="Click to edit measurements"
                        className="w-full rounded px-1 py-0.5 text-left text-xs text-slate-400 hover:bg-ink-800 hover:text-slate-200"
                      >
                        {piece.measurements.map((m) => `${m.name}: ${m.value}${m.unit}`).join(", ") ||
                          "—"}
                      </button>
                    </td>
                    <td className="p-3">
                      {token && (
                        <MaterialNotesCell token={token} piece={piece} onSaved={handlePieceUpdated} />
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {token && showMeasurementTypeModal && (
        <MeasurementTypeModal
          token={token}
          projectId={project.id}
          partNumbers={partNumbers}
          conditions={conditions}
          measurementTypes={measurementTypes}
          onClose={() => setShowMeasurementTypeModal(false)}
          onChanged={loadCatalogsAndProject}
        />
      )}

      {token && measurementsPiece && (
        <PieceMeasurementsModal
          token={token}
          piece={measurementsPiece}
          measurementTypes={measurementTypes}
          onClose={() => setMeasurementsPiece(null)}
          onSaved={handleMeasurementsSaved}
        />
      )}
    </AppShell>
  );
}
