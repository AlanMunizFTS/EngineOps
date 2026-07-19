import { useState } from "react";

type PhaseStatus = "done" | "current" | "next";

const PHASES: { label: string; status: PhaseStatus }[] = [
  { label: "Phase 0 — Foundations", status: "done" },
  { label: "Phase 1 — Projects, Machines, Implementations", status: "current" },
  { label: "Phase 2 — Issues, Kanban & Timeline", status: "next" },
];

const DOT_STYLES: Record<PhaseStatus, string> = {
  done: "bg-emerald-500",
  current: "bg-ember-500",
  next: "bg-ink-600",
};

export default function RoadmapCard() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div className="relative rounded-2xl border border-ink-800 bg-gradient-to-br from-ink-900 to-ink-850 p-5 shadow-lg shadow-black/20">
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="absolute right-3 top-3 text-slate-500 transition-colors hover:text-slate-200"
      >
        ×
      </button>
      <p className="text-xs font-semibold uppercase tracking-wide text-ember-400">Roadmap</p>
      <ul className="mt-3 space-y-2 text-sm">
        {PHASES.map((phase) => (
          <li key={phase.label} className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${DOT_STYLES[phase.status]}`} />
            <span className={phase.status === "next" ? "text-slate-500" : "text-slate-200"}>
              {phase.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
