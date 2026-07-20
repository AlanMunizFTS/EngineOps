import type { AreaStatusResponse } from "../api/client";
import { SparkleIcon } from "./icons";

interface PhaseToolsPanelProps {
  phaseStatus: AreaStatusResponse;
  isCurrentProjectPhase: boolean;
  onSetAsProjectPhase: () => void;
}

export default function PhaseToolsPanel({
  phaseStatus,
  isCurrentProjectPhase,
  onSetAsProjectPhase,
}: PhaseToolsPanelProps) {
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
    </div>
  );
}
