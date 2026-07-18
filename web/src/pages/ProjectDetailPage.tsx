import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

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
    return <div className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</div>;
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white px-8 py-4 shadow">
        <Link to="/projects" className="text-sm text-slate-500 hover:text-slate-900">
          ← Projects
        </Link>
        <h1 className="text-lg font-semibold text-slate-900">{project.name}</h1>
        {project.description && <p className="text-sm text-slate-500">{project.description}</p>}
      </header>

      <main className="mx-auto max-w-5xl space-y-6 p-8">
        {error && <p className="text-sm text-red-600">{error}</p>}

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
      </main>
    </div>
  );
}
