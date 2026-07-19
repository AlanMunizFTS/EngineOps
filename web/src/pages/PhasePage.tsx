import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  getProject,
  listAreaStatuses,
  listProjectAreas,
  updateProjectAreaStatus,
  type AreaStatusResponse,
  type ProjectAreaResponse,
  type ProjectResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import PhaseToolsPanel from "../components/PhaseToolsPanel";
import ProjectTabs from "../components/ProjectTabs";

export default function PhasePage() {
  const { projectId, statusId } = useParams<{ projectId: string; statusId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [phase, setPhase] = useState<ProjectAreaResponse | undefined>(undefined);
  const [statuses, setStatuses] = useState<AreaStatusResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, areas] = await Promise.all([
        getProject(token, projectId),
        listProjectAreas(token, projectId),
      ]);
      setProject(projectData);
      const current = areas[0];
      setPhase(current);
      if (current) {
        setStatuses(await listAreaStatuses(token, current.area_type.id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load phase");
    }
  }

  async function handleSetAsProjectPhase() {
    if (!token || !projectId || !phase || !statusId) return;
    try {
      await updateProjectAreaStatus(token, projectId, phase.id, statusId);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update phase");
    }
  }

  const viewingStatus = statuses.find((status) => status.id === statusId);

  if (!project || !viewingStatus) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto max-w-3xl space-y-4 p-6">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <PhaseToolsPanel
          phaseStatus={viewingStatus}
          isCurrentProjectPhase={viewingStatus.id === phase?.status.id}
          onSetAsProjectPhase={handleSetAsProjectPhase}
        />
      </div>
    </AppShell>
  );
}
