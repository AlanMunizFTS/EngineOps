import { useState } from "react";
import type { MouseEvent } from "react";
import { Link } from "react-router-dom";

import {
  listMachineImplementations,
  listPlantMachines,
  listProjectAreas,
  listProjectPlants,
  type AreaStatusResponse,
  type ImplementationResponse,
  type MachineResponse,
  type PlantResponse,
  type ProjectResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { BuildingIcon, ChevronDownIcon, FolderIcon } from "./icons";

function ProjectIcon({ name }: { name: string }) {
  return (
    <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-ink-700 text-[10px] font-semibold text-slate-300">
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <ChevronDownIcon
      className={`h-3 w-3 flex-shrink-0 text-slate-600 transition-transform ${
        expanded ? "" : "-rotate-90"
      }`}
    />
  );
}

function DeviationBadge({ phaseName }: { phaseName: string }) {
  return (
    <span
      title={`Phase overridden: ${phaseName}`}
      className="ml-auto flex-shrink-0 rounded bg-amber-500/20 px-1 text-[10px] font-bold leading-4 text-amber-400"
    >
      M
    </span>
  );
}

function EffectivePhaseLabel({ phase }: { phase: AreaStatusResponse | null }) {
  if (!phase) return null;
  return <span className="flex-shrink-0 text-[10px] text-slate-600">{phase.name}</span>;
}

function ImplementationRow({
  implementation,
  inheritedPhase,
}: {
  implementation: ImplementationResponse;
  inheritedPhase: AreaStatusResponse | null;
}) {
  const effective = implementation.phase_status ?? inheritedPhase;

  return (
    <div className="flex items-center gap-1.5 py-1 pl-20 pr-2 text-sm text-slate-400 hover:bg-ink-800">
      <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-ink-600" />
      <span className="truncate">{implementation.label}</span>
      <EffectivePhaseLabel phase={effective} />
      {implementation.phase_status && (
        <DeviationBadge phaseName={implementation.phase_status.name} />
      )}
    </div>
  );
}

function MachineRow({
  machine,
  inheritedPhase,
}: {
  machine: MachineResponse;
  inheritedPhase: AreaStatusResponse | null;
}) {
  const { token } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [implementations, setImplementations] = useState<ImplementationResponse[] | null>(null);

  const effective = machine.phase_status ?? inheritedPhase;

  async function toggle() {
    if (!expanded && implementations === null && token) {
      setImplementations(await listMachineImplementations(token, machine.id));
    }
    setExpanded((prev) => !prev);
  }

  return (
    <div>
      <button
        onClick={toggle}
        className="flex w-full items-center gap-1.5 py-1 pl-14 pr-2 text-left text-sm text-slate-300 transition-colors hover:bg-ink-800"
      >
        <Chevron expanded={expanded} />
        <FolderIcon className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
        <span className="truncate">{machine.name}</span>
        <EffectivePhaseLabel phase={effective} />
        {machine.phase_status && <DeviationBadge phaseName={machine.phase_status.name} />}
      </button>

      {expanded && implementations && (
        <div>
          {implementations.map((implementation) => (
            <ImplementationRow
              key={implementation.id}
              implementation={implementation}
              inheritedPhase={effective}
            />
          ))}
          {implementations.length === 0 && (
            <p className="py-1 pl-20 text-xs text-slate-600">No implementations yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function PlantRow({
  plant,
  inheritedPhase,
}: {
  plant: PlantResponse;
  inheritedPhase: AreaStatusResponse | null;
}) {
  const { token } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [machines, setMachines] = useState<MachineResponse[] | null>(null);

  const effective = plant.phase_status ?? inheritedPhase;

  async function toggle() {
    if (!expanded && machines === null && token) {
      setMachines(await listPlantMachines(token, plant.id));
    }
    setExpanded((prev) => !prev);
  }

  return (
    <div>
      <button
        onClick={toggle}
        className="flex w-full items-center gap-1.5 py-1 pl-8 pr-2 text-left text-sm text-slate-300 transition-colors hover:bg-ink-800"
      >
        <Chevron expanded={expanded} />
        <BuildingIcon className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
        <span className="truncate">{plant.name}</span>
        <EffectivePhaseLabel phase={effective} />
        {plant.phase_status && <DeviationBadge phaseName={plant.phase_status.name} />}
      </button>

      {expanded && machines && (
        <div>
          {machines.map((machine) => (
            <MachineRow key={machine.id} machine={machine} inheritedPhase={effective} />
          ))}
          {machines.length === 0 && (
            <p className="py-1 pl-14 text-xs text-slate-600">No machines yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function ProjectNode({ project, isActive }: { project: ProjectResponse; isActive: boolean }) {
  const { token } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [projectPhase, setProjectPhase] = useState<AreaStatusResponse | null>(null);
  const [plants, setPlants] = useState<PlantResponse[] | null>(null);

  async function toggleExpand(event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!token) return;
    if (!expanded && plants === null) {
      const [areas, plantData] = await Promise.all([
        listProjectAreas(token, project.id),
        listProjectPlants(token, project.id),
      ]);
      setProjectPhase(areas[0]?.status ?? null);
      setPlants(plantData);
    }
    setExpanded((prev) => !prev);
  }

  return (
    <div>
      <div
        className={`flex items-center gap-1 rounded-md pr-2 text-sm transition-colors ${
          isActive ? "bg-ember-500/10 text-ember-400" : "text-slate-300 hover:bg-ink-800"
        }`}
      >
        <button
          onClick={toggleExpand}
          className="flex-shrink-0 p-1.5 text-slate-500 hover:text-slate-300"
          aria-label="Toggle"
        >
          <Chevron expanded={expanded} />
        </button>
        <Link to={`/projects/${project.id}`} className="flex flex-1 items-center gap-2 truncate py-1">
          <ProjectIcon name={project.name} />
          <span className="truncate">{project.name}</span>
        </Link>
      </div>

      {expanded && plants && (
        <div>
          {plants.map((plant) => (
            <PlantRow key={plant.id} plant={plant} inheritedPhase={projectPhase} />
          ))}
          {plants.length === 0 && (
            <p className="py-1 pl-8 text-xs text-slate-600">No plants yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProjectTree({
  projects,
  activeProjectId,
}: {
  projects: ProjectResponse[];
  activeProjectId?: string;
}) {
  return (
    <div className="space-y-0.5">
      {projects.map((project) => (
        <ProjectNode
          key={project.id}
          project={project}
          isActive={project.id === activeProjectId}
        />
      ))}
    </div>
  );
}
