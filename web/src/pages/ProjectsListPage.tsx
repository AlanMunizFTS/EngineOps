import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { createProject, listProjects, type ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Brand from "../components/Brand";

export default function ProjectsListPage() {
  const { token, user, logout } = useAuth();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (token) {
      void refreshProjects(token);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function refreshProjects(authToken: string) {
    setIsLoading(true);
    try {
      setProjects(await listProjects(authToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !name.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      await createProject(token, name.trim(), description.trim());
      setName("");
      setDescription("");
      await refreshProjects(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="flex items-center justify-between border-b border-ink-800 bg-ink-900/70 px-8 py-4 backdrop-blur">
        <Brand subtitle="Projects" />
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span>{user?.email}</span>
          <button onClick={logout} className="text-slate-500 transition-colors hover:text-ember-400">
            Log out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-8">
        <form
          onSubmit={handleCreate}
          className="space-y-3 rounded-2xl border border-ink-800 bg-ink-900 p-6 shadow-lg shadow-black/20"
        >
          <h2 className="text-base font-semibold text-slate-100">New project</h2>
          <input
            type="text"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
            rows={2}
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={isCreating}
            className="rounded-lg bg-ember-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-ember-600 disabled:opacity-50"
          >
            {isCreating ? "Creating..." : "Create project"}
          </button>
        </form>

        <div className="rounded-2xl border border-ink-800 bg-ink-900 shadow-lg shadow-black/20">
          <h2 className="border-b border-ink-800 px-6 py-4 text-base font-semibold text-slate-100">
            Projects
          </h2>
          {isLoading ? (
            <p className="p-6 text-sm text-slate-500">Loading...</p>
          ) : projects.length === 0 ? (
            <p className="p-6 text-sm text-slate-500">No projects yet.</p>
          ) : (
            <ul className="divide-y divide-ink-800">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link
                    to={`/projects/${project.id}`}
                    className="group block px-6 py-4 transition-colors hover:bg-ink-850"
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
      </main>
    </div>
  );
}
