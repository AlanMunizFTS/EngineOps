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
  listProjectMembers,
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
import ProjectMachines, { type MachineWithImplementations } from "../components/ProjectMachines";
import ProjectTabs from "../components/ProjectTabs";
import ProjectTimeline from "../components/ProjectTimeline";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [areas, setAreas] = useState<ProjectAreaResponse[]>([]);
  const [statusOptions, setStatusOptions] = useState<Record<string, AreaStatusResponse[]>>({});
  const [machines, setMachines] = useState<MachineWithImplementations[]>([]);
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
      const [projectData, areaData, machineData, timelineData, memberData] = await Promise.all([
        getProject(authToken, id),
        listProjectAreas(authToken, id),
        listProjectMachines(authToken, id),
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

  const latestActivity = timeline[timeline.length - 1];

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs />

      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-8 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-6">
          {error && <p className="text-sm text-red-400">{error}</p>}

          <ProjectAreaTiles
            areas={areas}
            statusOptions={statusOptions}
            onStatusChange={handleStatusChange}
          />

          {latestActivity && (
            <div className="flex items-center gap-2 rounded-xl border border-ink-800 bg-ink-900 px-4 py-2.5 text-sm text-slate-400">
              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-ember-500 text-[10px] font-semibold text-white">
                {project.name.charAt(0).toUpperCase()}
              </span>
              <span className="truncate">Latest: {latestActivity.action}</span>
              <span className="ml-auto flex-shrink-0 text-xs text-slate-500">
                {new Date(latestActivity.occurred_at).toLocaleString()}
              </span>
            </div>
          )}

          <ProjectMachines
            machines={machines}
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
