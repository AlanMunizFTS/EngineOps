import type { AuditLogEntryResponse } from "../api/client";

export default function ProjectTimeline({ entries }: { entries: AuditLogEntryResponse[] }) {
  return (
    <section className="rounded-2xl border border-ink-800 bg-ink-900 p-6 shadow-lg shadow-black/20">
      <h2 className="mb-4 text-base font-semibold text-slate-100">Timeline</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No activity yet.</p>
      ) : (
        <ul className="space-y-3 border-l border-ink-700 pl-4">
          {entries.map((entry) => (
            <li key={entry.id} className="relative text-sm">
              <span className="absolute -left-[1.1rem] top-1.5 h-2 w-2 rounded-full bg-ember-500" />
              <span className="text-slate-200">{entry.action}</span>
              <span className="ml-2 text-xs text-slate-500">
                {new Date(entry.occurred_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
