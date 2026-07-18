import type { AuditLogEntryResponse } from "../api/client";

export default function ProjectTimeline({ entries }: { entries: AuditLogEntryResponse[] }) {
  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Timeline</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No activity yet.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map((entry) => (
            <li key={entry.id} className="text-sm text-slate-700">
              <span className="text-slate-400">
                {new Date(entry.occurred_at).toLocaleString()} ·{" "}
              </span>
              {entry.action}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
