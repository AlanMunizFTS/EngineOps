import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  createImplementation,
  createMachine,
  getProject,
  getProjectTimeline,
  listAreaStatuses,
  listMachineImplementations,
  listProjectAreas,
  listProjectMachines,
  updateProjectAreaStatus,
  type AreaStatusResponse,
  type AuditLogEntryResponse,
  type ImplementationStatus,
  type ProjectAreaResponse,
  type ProjectResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import ProjectAreaTiles from "../components/ProjectAreaTiles";
import ProjectMachines, { type MachineWithImplementations } from "../components/ProjectMachines";
import ProjectTimeline from "../components/ProjectTimeline";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [areas, setAreas] = useState<ProjectAreaResponse[]>([]);
  const [statusOptions, setStatusOptions] = useState<Record<string, AreaStatusResponse[]>>({});
  const [machines, setMachines] = useState<MachineWithImplementations[]>([]);
  const [timeline, setTimeline] = useState<AuditLogEntryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) {
      void loadAll(token, projectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll(authToken: string, id: string) {
    try {
      const [projectData, areaData, machineData, timelineData] = await Promise.all([
        getProject(authToken, id),
        listProjectAreas(authToken, id),
        listProjectMachines(authToken, id),
        getProjectTimeline(authToken, id),
      ]);
      setProject(projectData);
      setAreas(areaData);
      setTimeline(timelineData);

      const statusEntries = await Promise.all(
        areaData.map(
          async (area) =>
            [area.area_type.id, await listAreaStatuses(authToken, area.area_type.id)] as const,
        ),
      );
      setStatusOptions(Object.fromEntries(statusEntries));

      const machinesWithImplementations = await Promise.all(
        machineData.map(async (machine) => ({
          ...machine,
          implementations: await listMachineImplementations(authToken, machine.id),
        })),
      );
      setMachines(machinesWithImplementations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    }
  }

  async function handleStatusChange(area: ProjectAreaResponse, statusId: string) {
    if (!token || !projectId) return;
    try {
      await updateProjectAreaStatus(token, projectId, area.id, statusId);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleAddMachine(name: string, machineType: string, location: string) {
    if (!token || !projectId) return;
    try {
      await createMachine(token, projectId, name, machineType, location);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create machine");
    }
  }

  async function handleAddImplementation(
    machineId: string,
    label: string,
    status: ImplementationStatus,
  ) {
    if (!token || !projectId) return;
    try {
      await createImplementation(token, machineId, label, status);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create implementation");
    }
  }

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6 p-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">{project.name}</h1>
          {project.description && (
            <p className="mt-1 text-sm text-slate-500">{project.description}</p>
          )}
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <ProjectAreaTiles
          areas={areas}
          statusOptions={statusOptions}
          onStatusChange={handleStatusChange}
        />
        <ProjectMachines
          machines={machines}
          onAddMachine={handleAddMachine}
          onAddImplementation={handleAddImplementation}
        />
        <ProjectTimeline entries={timeline} />
      </div>
    </AppShell>
  );
}
