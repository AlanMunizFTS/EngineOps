import type { AreaStatusResponse } from "../api/client";
import { SparkleIcon } from "./icons";

interface ImplementationPhasePanelProps {
  breadcrumb: string;
  implementationLabel: string;
  effectivePhaseId: string | undefined;
  hasOverride: boolean;
  statuses: AreaStatusResponse[];
  onSetPhase: (statusId: string) => void;
  onClearOverride: () => void;
  onClose: () => void;
}

export default function ImplementationPhasePanel({
  breadcrumb,
  implementationLabel,
  effectivePhaseId,
  hasOverride,
  statuses,
  onSetPhase,
  onClearOverride,
  onClose,
}: ImplementationPhasePanelProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500">{breadcrumb}</p>
          <h1 className="text-2xl font-semibold text-slate-100">{implementationLabel}</h1>
          <p className="text-sm text-slate-500">
            {hasOverride ? "Phase overridden for this implementation" : "Inheriting phase"}
          </p>
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 text-sm text-slate-500 transition-colors hover:text-slate-300"
        >
          ← Back
        </button>
      </div>

      <div className="rounded-md border border-ink-800 bg-ink-900 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100">Phase</h2>
          {hasOverride && (
            <button
              onClick={onClearOverride}
              className="text-xs font-medium text-slate-500 transition-colors hover:text-ember-400"
            >
              Clear override (inherit again)
            </button>
          )}
        </div>
        <div className="space-y-0.5">
          {statuses.map((status) => {
            const isCurrent = status.id === effectivePhaseId;
            return (
              <button
                key={status.id}
                onClick={() => onSetPhase(status.id)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                  isCurrent
                    ? "bg-ember-500/10 text-ember-400"
                    : "text-slate-300 hover:bg-ink-800"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                    isCurrent ? "bg-ember-500" : "bg-ink-600"
                  }`}
                />
                {status.name}
                {isCurrent && (
                  <span className="ml-auto flex-shrink-0 text-[10px] text-slate-500">
                    {hasOverride ? "override" : "inherited"}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-md border border-ink-800 bg-ink-900 p-6 text-center">
        <SparkleIcon className="mx-auto h-5 w-5 text-slate-600" />
        <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">
          AI-guided tools for this implementation are coming soon.
        </p>
      </div>
    </div>
  );
}
