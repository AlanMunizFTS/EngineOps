const TABS = [
  { label: "Code", active: true },
  { label: "Issues", comingSoon: true },
  { label: "Kanban", comingSoon: true },
  { label: "Settings", comingSoon: true },
];

export default function ProjectTabs() {
  return (
    <div className="flex gap-1 border-b border-ink-800 px-8">
      {TABS.map((tab) => {
        if (tab.active) {
          return (
            <span
              key={tab.label}
              className="border-b-2 border-ember-500 px-3 py-3 text-sm font-medium text-slate-100"
            >
              {tab.label}
            </span>
          );
        }
        return (
          <span
            key={tab.label}
            title="Coming soon"
            className="cursor-not-allowed px-3 py-3 text-sm text-slate-600"
          >
            {tab.label}
          </span>
        );
      })}
    </div>
  );
}
