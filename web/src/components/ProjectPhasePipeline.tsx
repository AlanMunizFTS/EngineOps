import type { AreaStatusResponse, ProjectAreaResponse } from "../api/client";

interface ProjectPhasePipelineProps {
  phase: ProjectAreaResponse | undefined;
  statuses: AreaStatusResponse[];
  onStatusChange: (statusId: string) => void;
}

export default function ProjectPhasePipeline({
  phase,
  statuses,
  onStatusChange,
}: ProjectPhasePipelineProps) {
  if (!phase) return null;

  const currentIndex = statuses.findIndex((status) => status.id === phase.status.id);

  return (
    <section className="rounded-md border border-ink-800 bg-ink-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Phase</h2>
        <span className="text-xs text-slate-500">
          Currently <span className="text-ember-400">{phase.status.name}</span> — click any
          phase to jump to it
        </span>
      </div>

      <div className="flex items-center overflow-x-auto pb-1">
        {statuses.map((status, index) => {
          const isCurrent = status.id === phase.status.id;
          const isPast = index < currentIndex;

          return (
            <div key={status.id} className="flex flex-1 items-center last:flex-none">
              <button
                onClick={() => onStatusChange(status.id)}
                title={status.name}
                className="group flex flex-shrink-0 flex-col items-center gap-1.5"
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full border-2 text-[10px] font-semibold transition-colors ${
                    isCurrent
                      ? "border-ember-500 bg-ember-500 text-white"
                      : isPast
                        ? "border-ember-500/60 bg-ember-500/10 text-ember-400"
                        : "border-ink-600 bg-ink-800 text-slate-500 group-hover:border-slate-500"
                  }`}
                >
                  {index + 1}
                </span>
                <span
                  className={`whitespace-nowrap text-[11px] ${
                    isCurrent ? "font-medium text-slate-100" : "text-slate-500"
                  }`}
                >
                  {status.name}
                </span>
              </button>

              {index < statuses.length - 1 && (
                <div className={`mx-1 h-px flex-1 ${isPast ? "bg-ember-500/50" : "bg-ink-700"}`} />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
