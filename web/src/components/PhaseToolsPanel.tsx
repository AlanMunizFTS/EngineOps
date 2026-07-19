import type { AreaStatusResponse } from "../api/client";
import type { PlantWithMachines } from "./ProjectPlants";
import { SparkleIcon } from "./icons";

interface FlatItem {
  type: "Plant" | "Machine" | "Implementation";
  id: string;
  label: string;
  effectivePhaseId: string | undefined;
  hasOverride: boolean;
}

function flattenWithPhases(
  plants: PlantWithMachines[],
  projectPhaseId: string | undefined,
): FlatItem[] {
  const items: FlatItem[] = [];

  for (const plant of plants) {
    const plantPhaseId = plant.phase_status?.id ?? projectPhaseId;
    items.push({
      type: "Plant",
      id: plant.id,
      label: plant.name,
      effectivePhaseId: plantPhaseId,
      hasOverride: Boolean(plant.phase_status),
    });

    for (const machine of plant.machines) {
      const machinePhaseId = machine.phase_status?.id ?? plantPhaseId;
      items.push({
        type: "Machine",
        id: machine.id,
        label: `${plant.name} / ${machine.name}`,
        effectivePhaseId: machinePhaseId,
        hasOverride: Boolean(machine.phase_status),
      });

      for (const implementation of machine.implementations) {
        const implPhaseId = implementation.phase_status?.id ?? machinePhaseId;
        items.push({
          type: "Implementation",
          id: implementation.id,
          label: `${plant.name} / ${machine.name} / ${implementation.label}`,
          effectivePhaseId: implPhaseId,
          hasOverride: Boolean(implementation.phase_status),
        });
      }
    }
  }

  return items;
}

interface PhaseToolsPanelProps {
  phaseStatus: AreaStatusResponse;
  isCurrentProjectPhase: boolean;
  projectPhaseId: string | undefined;
  plants: PlantWithMachines[];
  onSetAsProjectPhase: () => void;
  onSetPlantPhase: (plantId: string, statusId: string | null) => void;
  onSetMachinePhase: (machineId: string, statusId: string | null) => void;
  onSetImplementationPhase: (implementationId: string, statusId: string | null) => void;
}

export default function PhaseToolsPanel({
  phaseStatus,
  isCurrentProjectPhase,
  projectPhaseId,
  plants,
  onSetAsProjectPhase,
  onSetPlantPhase,
  onSetMachinePhase,
  onSetImplementationPhase,
}: PhaseToolsPanelProps) {
  const allItems = flattenWithPhases(plants, projectPhaseId);
  const inThisPhase = allItems.filter((item) => item.effectivePhaseId === phaseStatus.id);
  const notInThisPhase = allItems.filter((item) => item.effectivePhaseId !== phaseStatus.id);

  function moveToThisPhase(item: FlatItem) {
    if (item.type === "Plant") onSetPlantPhase(item.id, phaseStatus.id);
    if (item.type === "Machine") onSetMachinePhase(item.id, phaseStatus.id);
    if (item.type === "Implementation") onSetImplementationPhase(item.id, phaseStatus.id);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">{phaseStatus.name}</h1>
          <p className="text-sm text-slate-500">Tools for this phase</p>
        </div>
        {isCurrentProjectPhase ? (
          <span className="flex-shrink-0 rounded-md bg-ember-500/10 px-3 py-1.5 text-sm font-medium text-ember-400">
            Current project phase
          </span>
        ) : (
          <button
            onClick={onSetAsProjectPhase}
            className="flex-shrink-0 rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
          >
            Set as project phase
          </button>
        )}
      </div>

      <div className="rounded-md border border-ink-800 bg-ink-900 p-6 text-center">
        <SparkleIcon className="mx-auto h-5 w-5 text-slate-600" />
        <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">
          AI-guided {phaseStatus.name.toLowerCase()} tools are coming soon.
        </p>
      </div>

      <div className="rounded-md border border-ink-800 bg-ink-900">
        <h2 className="border-b border-ink-800 px-4 py-2 text-sm font-semibold text-slate-200">
          Currently in {phaseStatus.name} ({inThisPhase.length})
        </h2>
        <ul className="divide-y divide-ink-800">
          {inThisPhase.map((item) => (
            <li key={item.id} className="flex items-center gap-2 px-4 py-2 text-sm">
              <span className="flex-shrink-0 rounded bg-ink-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
                {item.type}
              </span>
              <span className="truncate text-slate-300">{item.label}</span>
              {item.hasOverride && (
                <span
                  title="Explicit phase override"
                  className="ml-auto flex-shrink-0 rounded bg-amber-500/20 px-1 text-[10px] font-bold leading-4 text-amber-400"
                >
                  M
                </span>
              )}
            </li>
          ))}
          {inThisPhase.length === 0 && (
            <li className="px-4 py-4 text-sm text-slate-500">Nothing in this phase yet.</li>
          )}
        </ul>
      </div>

      {notInThisPhase.length > 0 && (
        <div className="rounded-md border border-ink-800 bg-ink-900">
          <h2 className="border-b border-ink-800 px-4 py-2 text-sm font-semibold text-slate-200">
            Move into {phaseStatus.name}
          </h2>
          <ul className="divide-y divide-ink-800">
            {notInThisPhase.map((item) => (
              <li key={item.id} className="flex items-center gap-2 px-4 py-2 text-sm">
                <span className="flex-shrink-0 rounded bg-ink-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
                  {item.type}
                </span>
                <span className="truncate text-slate-400">{item.label}</span>
                <button
                  onClick={() => moveToThisPhase(item)}
                  className="ml-auto flex-shrink-0 text-xs font-medium text-ember-400 transition-colors hover:text-ember-300"
                >
                  Move here
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
