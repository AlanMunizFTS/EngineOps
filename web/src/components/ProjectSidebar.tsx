import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import type { ProjectResponse } from "../api/client";
import { BoardIcon, FolderIcon, HomeIcon, TaskIcon, SparkleIcon } from "./icons";
import ProjectTree from "./ProjectTree";

const COLLAPSED_LIMIT = 6;

interface NavItem {
  label: string;
  to?: string;
  icon: (props: { className?: string }) => JSX.Element;
  comingSoon?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Home", to: "/projects", icon: HomeIcon },
  { label: "All tasks", icon: TaskIcon, comingSoon: true },
  { label: "All projects", to: "/projects/all", icon: FolderIcon },
  { label: "My Kanban", to: "/my-kanban", icon: BoardIcon },
  { label: "AI assistant", icon: SparkleIcon, comingSoon: true },
];

function NavMenu() {
  const location = useLocation();

  return (
    <nav className="space-y-0.5 border-b border-ink-800 pb-3">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        if (item.comingSoon) {
          return (
            <span
              key={item.label}
              title="Coming soon"
              className="flex cursor-not-allowed items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-600"
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </span>
          );
        }
        const isActive = location.pathname === item.to;
        return (
          <Link
            key={item.label}
            to={item.to!}
            className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
              isActive
                ? "bg-ember-500/10 text-ember-400"
                : "text-slate-300 hover:bg-ink-800 hover:text-slate-100"
            }`}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function ProjectSidebar({
  projects,
  activeProjectId,
  isExpanded,
}: {
  projects: ProjectResponse[];
  activeProjectId?: string;
  isExpanded: boolean;
}) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  const filtered = projects.filter((project) =>
    project.name.toLowerCase().includes(search.toLowerCase()),
  );
  const visible = showAll ? filtered : filtered.slice(0, COLLAPSED_LIMIT);

  return (
    <aside className="hidden w-64 flex-shrink-0 flex-col overflow-y-auto border-r border-ink-800 bg-ink-900/40 p-4 md:flex">
      {isExpanded && <NavMenu />}

      <div className="mt-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Your projects
        </h2>
        <button
          onClick={() => navigate("/projects?create=1")}
          className="rounded-md bg-ink-700 px-2 py-1 text-xs font-medium text-slate-200 transition-colors hover:bg-ember-500 hover:text-white"
        >
          + New
        </button>
      </div>

      <input
        type="text"
        placeholder="Find a project..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mt-3 w-full rounded-lg border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
      />

      <div className="mt-3">
        <ProjectTree projects={visible} activeProjectId={activeProjectId} />
        {filtered.length === 0 && (
          <p className="px-2 py-1.5 text-sm text-slate-500">No projects found.</p>
        )}
      </div>

      {!showAll && filtered.length > COLLAPSED_LIMIT && (
        <button
          onClick={() => setShowAll(true)}
          className="mt-1 px-2 py-1 text-left text-xs text-slate-500 transition-colors hover:text-ember-400"
        >
          Show more
        </button>
      )}
    </aside>
  );
}
