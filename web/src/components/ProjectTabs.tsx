import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { listAreaStatuses, listProjectAreas, type AreaStatusResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";

interface StaticTab {
  label: string;
  suffix?: string;
  comingSoon?: boolean;
}

const LEADING_TABS: StaticTab[] = [
  { label: "Code" },
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
  const { token } = useAuth();
  const base = `/projects/${projectId}`;
  const [phaseStatuses, setPhaseStatuses] = useState<AreaStatusResponse[]>([]);

  useEffect(() => {
    if (!token) return;
    listProjectAreas(token, projectId).then(async (areas) => {
      const current = areas[0];
      if (current) {
        setPhaseStatuses(await listAreaStatuses(token, current.area_type.id));
      }
    });
  }, [token, projectId]);

  return (
    <div className="flex gap-1 border-b border-ink-800 px-8">
      {LEADING_TABS.map((tab) => {
        const to = tab.suffix ? `${base}/${tab.suffix}` : base;
        const isActive = tab.suffix
          ? location.pathname.startsWith(to)
          : location.pathname === base;
        return <TabLink key={tab.label} to={to} isActive={isActive} label={tab.label} />;
      })}

      {phaseStatuses.map((status) => {
        const to = `${base}/phase/${status.id}`;
        return (
          <TabLink
            key={status.id}
            to={to}
            isActive={location.pathname === to}
            label={status.name}
          />
        );
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
