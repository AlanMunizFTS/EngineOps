import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { createProject, listProjects, type ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";

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
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center justify-between bg-white px-8 py-4 shadow">
        <h1 className="text-lg font-semibold text-slate-900">EngineOps</h1>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <span>{user?.email}</span>
          <button onClick={logout} className="text-slate-500 hover:text-slate-900">
            Log out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-8">
        <form onSubmit={handleCreate} className="space-y-3 rounded-lg bg-white p-6 shadow">
          <h2 className="text-base font-semibold text-slate-900">New project</h2>
          <input
            type="text"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2"
            rows={2}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={isCreating}
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {isCreating ? "Creating..." : "Create project"}
          </button>
        </form>

        <div className="rounded-lg bg-white shadow">
          <h2 className="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900">
            Projects
          </h2>
          {isLoading ? (
            <p className="p-6 text-sm text-slate-500">Loading...</p>
          ) : projects.length === 0 ? (
            <p className="p-6 text-sm text-slate-500">No projects yet.</p>
          ) : (
            <ul className="divide-y divide-slate-200">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link
                    to={`/projects/${project.id}`}
                    className="block px-6 py-4 hover:bg-slate-50"
                  >
                    <p className="font-medium text-slate-900">{project.name}</p>
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
