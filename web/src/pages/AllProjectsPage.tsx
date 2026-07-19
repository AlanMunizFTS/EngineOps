import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listProjects, type ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";

export default function AllProjectsPage() {
  const { token } = useAuth();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    listProjects(token)
      .then(setProjects)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load projects"))
      .finally(() => setIsLoading(false));
  }, [token]);

  const filtered = projects.filter((project) =>
    project.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-2xl font-semibold text-slate-100">All projects</h1>

        <input
          type="text"
          placeholder="Find a project..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
        />

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-slate-500">No projects found.</p>
        ) : (
          <ul className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
            {filtered.map((project) => (
              <li key={project.id}>
                <Link
                  to={`/projects/${project.id}`}
                  className="group block px-4 py-3 transition-colors hover:bg-ink-850"
                >
                  <p className="font-medium text-slate-100 group-hover:text-ember-400">
                    {project.name}
                  </p>
                  {project.description && (
                    <p className="text-sm text-slate-500">{project.description}</p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
