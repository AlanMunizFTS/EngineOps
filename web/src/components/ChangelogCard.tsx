const CHANGELOG = [
  { tag: "Phase 2", title: "Tasks, kanban board, milestones, and a project-wide timeline" },
  { tag: "Phase 1", title: "Home dashboard, project sidebar, and cross-project activity feed" },
  { tag: "Phase 0", title: "JWT auth, Docker Compose stack, and CI" },
];

export default function ChangelogCard() {
  return (
    <div className="rounded-md border border-ink-800 bg-ink-900 p-4">
      <p className="text-sm font-semibold text-slate-100">Latest from our changelog</p>
      <ul className="mt-3 space-y-3">
        {CHANGELOG.map((entry) => (
          <li key={entry.title}>
            <p className="text-xs text-slate-500">{entry.tag}</p>
            <p className="text-sm text-slate-300">{entry.title}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
