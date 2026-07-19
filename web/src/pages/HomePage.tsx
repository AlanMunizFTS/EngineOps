import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { createProject, getRecentActivity, type ActivityEntryResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import AskBox from "../components/AskBox";
import ChangelogCard from "../components/ChangelogCard";
import RoadmapCard from "../components/RoadmapCard";

const INITIAL_LIMIT = 10;
const EXPANDED_LIMIT = 30;

const ACTION_LABELS: Record<string, string> = {
  "project.created": "created this project",
  "member.added": "added a member",
  "area.status_changed": "updated an area status",
  "machine.created": "added a machine",
  "implementation.created": "added an implementation",
  "implementation.superseded": "superseded an implementation",
};

function describeAction(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

export default function HomePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activity, setActivity] = useState<ActivityEntryResponse[]>([]);
  const [activityLimit, setActivityLimit] = useState(INITIAL_LIMIT);
  const [isLoadingActivity, setIsLoadingActivity] = useState(true);
  const [activityError, setActivityError] = useState<string | null>(null);

  const [showCreateForm, setShowCreateForm] = useState(searchParams.get("create") === "1");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    setIsLoadingActivity(true);
    getRecentActivity(token, activityLimit)
      .then(setActivity)
      .catch((err) =>
        setActivityError(err instanceof Error ? err.message : "Failed to load activity"),
      )
      .finally(() => setIsLoadingActivity(false));
  }, [token, activityLimit]);

  useEffect(() => {
    setShowCreateForm(searchParams.get("create") === "1");
  }, [searchParams]);

  function closeCreateForm() {
    setShowCreateForm(false);
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
      <div className="mx-auto flex max-w-6xl gap-6 p-8">
        <div className="min-w-0 flex-1 space-y-6">
          <h1 className="text-2xl font-semibold text-slate-100">Home</h1>

          <AskBox />

          {showCreateForm && (
            <form
              onSubmit={handleCreate}
              className="relative space-y-3 rounded-2xl border border-ink-800 bg-ink-900 p-6 shadow-lg shadow-black/20"
            >
              <button
                type="button"
                onClick={closeCreateForm}
                aria-label="Close"
                className="absolute right-4 top-4 text-slate-500 transition-colors hover:text-slate-200"
              >
                ×
              </button>
              <h2 className="text-base font-semibold text-slate-100">New project</h2>
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
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100">Feed</h2>
              <button
                disabled
                title="Coming soon"
                className="cursor-not-allowed rounded-lg border border-ink-700 px-3 py-1 text-xs text-slate-500"
              >
                Filter
              </button>
            </div>

            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-400">Recent activity</h3>
              {activity.length >= activityLimit && activityLimit < EXPANDED_LIMIT && (
                <button
                  onClick={() => setActivityLimit(EXPANDED_LIMIT)}
                  className="text-sm text-ember-400 hover:text-ember-300"
                >
                  See more
                </button>
              )}
            </div>

            {isLoadingActivity ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : activityError ? (
              <p className="text-sm text-red-400">{activityError}</p>
            ) : activity.length === 0 ? (
              <p className="text-sm text-slate-500">
                Nothing yet — create a project to get started.
              </p>
            ) : (
              <ul className="space-y-3">
                {activity.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-xl border border-ink-800 bg-ink-900 p-4 shadow-lg shadow-black/10"
                  >
                    <Link
                      to={`/projects/${item.project_id}`}
                      className="font-semibold text-slate-100 transition-colors hover:text-ember-400"
                    >
                      {item.project_name}
                    </Link>
                    <p className="mt-1 text-sm text-slate-400">{describeAction(item.action)}</p>
                    <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                      <span className="h-2 w-2 rounded-full bg-ember-500" />
                      <span className="capitalize">{item.entity_type}</span>
                      <span>·</span>
                      <span>{new Date(item.occurred_at).toLocaleString()}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="hidden w-80 flex-shrink-0 space-y-4 lg:block">
          <RoadmapCard />
          <ChangelogCard />
        </aside>
      </div>
    </AppShell>
  );
}
