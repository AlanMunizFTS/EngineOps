import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { listProjects, type ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Brand from "./Brand";

const COLLAPSED_LIMIT = 6;

export default function AppShell({ children }: { children: ReactNode }) {
  const { token, user, logout } = useAuth();
  const { projectId: activeProjectId } = useParams<{ projectId?: string }>();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!token) return;
    listProjects(token)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [token]);

  const filtered = projects.filter((project) =>
    project.name.toLowerCase().includes(search.toLowerCase()),
  );
  const visible = showAll ? filtered : filtered.slice(0, COLLAPSED_LIMIT);

  return (
    <div className="flex min-h-screen bg-ink-950">
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
                <span
                  className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                    isActive ? "bg-ember-500" : "bg-ink-600"
                  }`}
                />
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

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-ink-800 bg-ink-900/70 px-6 py-3 backdrop-blur">
          <Link to="/projects">
            <Brand />
          </Link>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="hidden sm:inline">{user?.email}</span>
            <button
              onClick={logout}
              className="text-slate-500 transition-colors hover:text-ember-400"
            >
              Log out
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
