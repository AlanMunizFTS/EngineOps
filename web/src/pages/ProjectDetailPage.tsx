import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

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
  updateImplementationPhase,
  updateMachinePhase,
  updatePlantPhase,
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
import ImplementationPhasePanel from "../components/ImplementationPhasePanel";
import PhaseToolsPanel from "../components/PhaseToolsPanel";
import ProjectAbout from "../components/ProjectAbout";
import ProjectPlants, { type PlantWithMachines } from "../components/ProjectPlants";
import ProjectTabs from "../components/ProjectTabs";
import ProjectTimeline from "../components/ProjectTimeline";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [phase, setPhase] = useState<ProjectAreaResponse | undefined>(undefined);
  const [phaseStatuses, setPhaseStatuses] = useState<AreaStatusResponse[]>([]);
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
      setTimeline(timelineData);
      setMembers(memberData);

      const currentPhase = areaData[0];
      setPhase(currentPhase);
      setPhaseStatuses(
        currentPhase ? await listAreaStatuses(authToken, currentPhase.area_type.id) : [],
      );

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

  async function handleSetProjectPhase(statusId: string) {
    if (!token || !projectId || !phase) return;
    try {
      await updateProjectAreaStatus(token, projectId, phase.id, statusId);
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

  function handleSelectImplementation(implementationId: string) {
    setSearchParams({ implementation: implementationId });
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

  async function handleSetPlantPhase(plantId: string, statusId: string | null) {
    if (!token || !projectId) return;
    try {
      await updatePlantPhase(token, plantId, statusId);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update plant phase");
    }
  }

  async function handleSetMachinePhase(machineId: string, statusId: string | null) {
    if (!token || !projectId) return;
    try {
      await updateMachinePhase(token, machineId, statusId);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update machine phase");
    }
  }

  async function handleSetImplementationPhase(implementationId: string, statusId: string | null) {
    if (!token || !projectId) return;
    try {
      await updateImplementationPhase(token, implementationId, statusId);
      await loadAll(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update implementation phase");
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
  const viewingPhaseId = searchParams.get("phase");
  const viewingPhase = phaseStatuses.find((status) => status.id === viewingPhaseId);

  const viewingImplementationId = searchParams.get("implementation");
  let implementationContext:
    | {
        breadcrumb: string;
        implementation: PlantWithMachines["machines"][number]["implementations"][number];
        effectivePhaseId: string | undefined;
      }
    | undefined;
  if (viewingImplementationId) {
    for (const plant of plants) {
      for (const machine of plant.machines) {
        const implementation = machine.implementations.find(
          (item) => item.id === viewingImplementationId,
        );
        if (implementation) {
          const plantPhaseId = plant.phase_status?.id ?? phase?.status.id;
          const machinePhaseId = machine.phase_status?.id ?? plantPhaseId;
          implementationContext = {
            breadcrumb: `${plant.name} / ${machine.name}`,
            implementation,
            effectivePhaseId: implementation.phase_status?.id ?? machinePhaseId,
          };
        }
      }
    }
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs />

      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-4">
          {error && <p className="text-sm text-red-400">{error}</p>}

          {implementationContext ? (
            <ImplementationPhasePanel
              breadcrumb={implementationContext.breadcrumb}
              implementationLabel={implementationContext.implementation.label}
              effectivePhaseId={implementationContext.effectivePhaseId}
              hasOverride={Boolean(implementationContext.implementation.phase_status)}
              statuses={phaseStatuses}
              onSetPhase={(statusId) =>
                handleSetImplementationPhase(implementationContext!.implementation.id, statusId)
              }
              onClearOverride={() =>
                handleSetImplementationPhase(implementationContext!.implementation.id, null)
              }
              onClose={() => setSearchParams({})}
            />
          ) : viewingPhase ? (
            <PhaseToolsPanel
              phaseStatus={viewingPhase}
              isCurrentProjectPhase={viewingPhase.id === phase?.status.id}
              projectPhaseId={phase?.status.id}
              plants={plants}
              onSetAsProjectPhase={() => handleSetProjectPhase(viewingPhase.id)}
              onSetPlantPhase={handleSetPlantPhase}
              onSetMachinePhase={handleSetMachinePhase}
              onSetImplementationPhase={handleSetImplementationPhase}
            />
          ) : (
            <>
              <ProjectPlants
                plants={plants}
                latestActivityLabel={latestActivity?.action}
                latestActivityAt={
                  latestActivity
                    ? new Date(latestActivity.occurred_at).toLocaleString()
                    : undefined
                }
                onAddPlant={handleAddPlant}
                onAddMachine={handleAddMachine}
                onAddImplementation={handleAddImplementation}
                onSelectImplementation={handleSelectImplementation}
              />

              <div id="timeline">
                <ProjectTimeline entries={timeline} />
              </div>
            </>
          )}
        </div>

        <ProjectAbout description={project.description} members={members} />
      </div>
    </AppShell>
  );
}
