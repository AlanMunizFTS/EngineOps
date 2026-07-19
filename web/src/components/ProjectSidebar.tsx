import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { ProjectResponse } from "../api/client";

const COLLAPSED_LIMIT = 6;

function ProjectIcon({ name }: { name: string }) {
  return (
    <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-ink-700 text-[10px] font-semibold text-slate-300">
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

export default function ProjectSidebar({
  projects,
  activeProjectId,
}: {
  projects: ProjectResponse[];
  activeProjectId?: string;
}) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  const filtered = projects.filter((project) =>
    project.name.toLowerCase().includes(search.toLowerCase()),
  );
  const visible = showAll ? filtered : filtered.slice(0, COLLAPSED_LIMIT);

  return (
    <aside className="hidden w-64 flex-shrink-0 flex-col border-r border-ink-800 bg-ink-900/40 p-4 md:flex">
      <div className="flex items-center justify-between">
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

      <nav className="mt-3 flex-1 space-y-0.5 overflow-y-auto">
        {visible.map((project) => {
          const isActive = project.id === activeProjectId;
          return (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
                isActive
                  ? "bg-ember-500/10 text-ember-400"
                  : "text-slate-300 hover:bg-ink-800 hover:text-slate-100"
              }`}
            >
              <ProjectIcon name={project.name} />
              <span className="truncate">{project.name}</span>
            </Link>
          );
        })}
        {filtered.length === 0 && (
          <p className="px-2 py-1.5 text-sm text-slate-500">No projects found.</p>
        )}
      </nav>

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
