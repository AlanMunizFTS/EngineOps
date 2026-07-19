import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  createImplementation,
  createMachine,
  createPlant,
  getProject,
  getProjectTimeline,
  listAreaStatuses,
  listMachineImplementations,
  listPlantMachines,
  listProjectAreas,
  listProjectMembers,
  listProjectPlants,
  updateProjectAreaStatus,
  type AreaStatusResponse,
  type AuditLogEntryResponse,
  type ImplementationStatus,
  type ProjectAreaResponse,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import ProjectAbout from "../components/ProjectAbout";
import ProjectAreaTiles from "../components/ProjectAreaTiles";
import ProjectPlants, { type PlantWithMachines } from "../components/ProjectPlants";
import ProjectTabs from "../components/ProjectTabs";
import ProjectTimeline from "../components/ProjectTimeline";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [areas, setAreas] = useState<ProjectAreaResponse[]>([]);
  const [statusOptions, setStatusOptions] = useState<Record<string, AreaStatusResponse[]>>({});
  const [plants, setPlants] = useState<PlantWithMachines[]>([]);
  const [timeline, setTimeline] = useState<AuditLogEntryResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) {
      void loadAll(token, projectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll(authToken: string, id: string) {
    try {
      const [projectData, areaData, plantData, timelineData, memberData] = await Promise.all([
        getProject(authToken, id),
        listProjectAreas(authToken, id),
        listProjectPlants(authToken, id),
        getProjectTimeline(authToken, id),
        listProjectMembers(authToken, id),
      ]);
      setProject(projectData);
      setAreas(areaData);
      setTimeline(timelineData);
      setMembers(memberData);

      const statusEntries = await Promise.all(
        areaData.map(
          async (area) =>
            [area.area_type.id, await listAreaStatuses(authToken, area.area_type.id)] as const,
        ),
      );
      setStatusOptions(Object.fromEntries(statusEntries));

      const plantsWithMachines = await Promise.all(
        plantData.map(async (plant) => {
          const machineData = await listPlantMachines(authToken, plant.id);
          const machinesWithImplementations = await Promise.all(
            machineData.map(async (machine) => ({
              ...machine,
              implementations: await listMachineImplementations(authToken, machine.id),
            })),
          );
          return { ...plant, machines: machinesWithImplementations };
        }),
      );
      setPlants(plantsWithMachines);
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

  async function handleAddPlant(name: string, location: string) {
    if (!token || !projectId) return;
    try {
      await createPlant(token, projectId, name, location);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create plant");
    }
  }

  async function handleAddMachine(
    plantId: string,
    name: string,
    machineType: string,
    location: string,
  ) {
    if (!token || !projectId) return;
    try {
      await createMachine(token, plantId, name, machineType, location);
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

  const latestActivity = timeline[timeline.length - 1];

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs />

      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-4">
          {error && <p className="text-sm text-red-400">{error}</p>}

          <ProjectAreaTiles
            areas={areas}
            statusOptions={statusOptions}
            onStatusChange={handleStatusChange}
          />

          <ProjectPlants
            plants={plants}
            latestActivityLabel={latestActivity?.action}
            latestActivityAt={
              latestActivity ? new Date(latestActivity.occurred_at).toLocaleString() : undefined
            }
            onAddPlant={handleAddPlant}
            onAddMachine={handleAddMachine}
            onAddImplementation={handleAddImplementation}
          />

          <div id="timeline">
            <ProjectTimeline entries={timeline} />
          </div>
        </div>

        <ProjectAbout description={project.description} members={members} />
      </div>
    </AppShell>
  );
}
