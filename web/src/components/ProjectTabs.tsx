import { Link, useLocation } from "react-router-dom";

interface StaticTab {
  label: string;
  suffix?: string;
  comingSoon?: boolean;
}

const LEADING_TABS: StaticTab[] = [
  { label: "Dashboard" },
  { label: "Issues", suffix: "issues" },
  { label: "Kanban", suffix: "kanban" },
  { label: "Milestones", suffix: "milestones" },
];

const TRAILING_TABS: StaticTab[] = [{ label: "Settings", comingSoon: true }];

function TabLink({ to, isActive, label }: { to: string; isActive: boolean; label: string }) {
  return (
    <Link
      to={to}
      className={`border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
        isActive
          ? "border-ember-500 text-slate-100"
          : "border-transparent text-slate-400 hover:text-slate-100"
      }`}
    >
      {label}
    </Link>
  );
}

export default function ProjectTabs({ projectId }: { projectId: string }) {
  const location = useLocation();
  const base = `/projects/${projectId}`;

  return (
    <div className="flex gap-1 border-b border-ink-800 px-8">
      {LEADING_TABS.map((tab) => {
        const to = tab.suffix ? `${base}/${tab.suffix}` : base;
        const isActive = tab.suffix
          ? location.pathname.startsWith(to)
          : location.pathname === base;
        return <TabLink key={tab.label} to={to} isActive={isActive} label={tab.label} />;
      })}

      {TRAILING_TABS.map((tab) => (
        <span
          key={tab.label}
          title="Coming soon"
          className="cursor-not-allowed px-3 py-3 text-sm text-slate-600"
        >
          {tab.label}
        </span>
      ))}
    </div>
  );
}
