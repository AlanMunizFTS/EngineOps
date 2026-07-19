import { Link, useLocation } from "react-router-dom";

interface Tab {
  label: string;
  suffix?: string;
  comingSoon?: boolean;
}

const TABS: Tab[] = [
  { label: "Code" },
  { label: "Issues", suffix: "issues" },
  { label: "Kanban", suffix: "kanban" },
  { label: "Milestones", suffix: "milestones" },
  { label: "Settings", comingSoon: true },
];

export default function ProjectTabs({ projectId }: { projectId: string }) {
  const location = useLocation();
  const base = `/projects/${projectId}`;

  return (
    <div className="flex gap-1 border-b border-ink-800 px-8">
      {TABS.map((tab) => {
        if (tab.comingSoon) {
          return (
            <span
              key={tab.label}
              title="Coming soon"
              className="cursor-not-allowed px-3 py-3 text-sm text-slate-600"
            >
              {tab.label}
            </span>
          );
        }
        const to = tab.suffix ? `${base}/${tab.suffix}` : base;
        const isActive = tab.suffix
          ? location.pathname.startsWith(to)
          : location.pathname === base;
        return (
          <Link
            key={tab.label}
            to={to}
            className={`border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
              isActive
                ? "border-ember-500 text-slate-100"
                : "border-transparent text-slate-400 hover:text-slate-100"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
