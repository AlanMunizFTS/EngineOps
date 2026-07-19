import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { createProject, getRecentActivity, type ActivityEntryResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";

export default function HomePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activity, setActivity] = useState<ActivityEntryResponse[]>([]);
  const [isLoadingActivity, setIsLoadingActivity] = useState(true);
  const [activityError, setActivityError] = useState<string | null>(null);

  const [showCreateForm, setShowCreateForm] = useState(searchParams.get("create") === "1");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    getRecentActivity(token)
      .then(setActivity)
      .catch((err) =>
        setActivityError(err instanceof Error ? err.message : "Failed to load activity"),
      )
      .finally(() => setIsLoadingActivity(false));
  }, [token]);

  function toggleCreateForm() {
    setShowCreateForm((prev) => !prev);
    setSearchParams({});
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !name.trim()) return;
    setIsCreating(true);
    setFormError(null);
    try {
      const project = await createProject(token, name.trim(), description.trim());
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create project");
      setIsCreating(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6 p-8">
        <h1 className="text-2xl font-semibold text-slate-100">Home</h1>

        <button
          onClick={toggleCreateForm}
          className="rounded-lg bg-ember-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-ember-600"
        >
          New project
        </button>

        {showCreateForm && (
          <form
            onSubmit={handleCreate}
            className="space-y-3 rounded-2xl border border-ink-800 bg-ink-900 p-6 shadow-lg shadow-black/20"
          >
            <input
              type="text"
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
              className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
            />
            <textarea
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
            />
            {formError && <p className="text-sm text-red-400">{formError}</p>}
            <button
              type="submit"
              disabled={isCreating}
              className="rounded-lg bg-ember-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-ember-600 disabled:opacity-50"
            >
              {isCreating ? "Creating..." : "Create project"}
            </button>
          </form>
        )}

        <section>
          <h2 className="mb-3 text-base font-semibold text-slate-100">Recent activity</h2>
          {isLoadingActivity ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : activityError ? (
            <p className="text-sm text-red-400">{activityError}</p>
          ) : activity.length === 0 ? (
            <p className="text-sm text-slate-500">
              Nothing yet — create a project to get started.
            </p>
          ) : (
            <ul className="divide-y divide-ink-800 rounded-2xl border border-ink-800 bg-ink-900 shadow-lg shadow-black/20">
              {activity.map((item) => (
                <li key={item.id} className="px-5 py-3">
                  <Link
                    to={`/projects/${item.project_id}`}
                    className="font-medium text-slate-100 transition-colors hover:text-ember-400"
                  >
                    {item.project_name}
                  </Link>
                  <p className="text-sm text-slate-400">
                    {item.action}
                    <span className="ml-2 text-xs text-slate-500">
                      {new Date(item.occurred_at).toLocaleString()}
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}
