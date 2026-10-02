import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  createProject,
  getRecentActivity,
  listProjectMembers,
  listProjects,
  type ActivityEntryResponse,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import {
  createTask,
  listMilestones,
  listProjectTasks,
  updateTask,
  updateTaskStatus,
  type MilestoneResponse,
  type TaskPriority,
  type TaskResponse,
  type TaskStatus,
  type TaskType,
} from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import AskBox from "../components/AskBox";
import AssigneeMultiSelect from "../components/AssigneeMultiSelect";
import ChangelogCard from "../components/ChangelogCard";
import Modal, { ModalActions } from "../components/Modal";
import RoadmapCard from "../components/RoadmapCard";
import WeeklyPlanBoard from "../components/WeeklyPlanBoard";

const INITIAL_LIMIT = 10;
const EXPANDED_LIMIT = 30;

const ACTION_LABELS: Record<string, string> = {
  "project.created": "created this project",
  "member.added": "added a member",
  "area.status_changed": "updated the project phase",
  "task.created": "created a Task",
  "subtask.created": "created a Subtask",
  "task.status_changed": "moved a Task",
  "subtask.status_changed": "moved a Subtask",
  "milestone.created": "created a Milestone",
  "milestone.updated": "updated a Milestone",
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
  const [weeklyTasks, setWeeklyTasks] = useState<TaskResponse[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [isLoadingPlan, setIsLoadingPlan] = useState(true);
  const [planError, setPlanError] = useState<string | null>(null);

  const [showCreateForm, setShowCreateForm] = useState(searchParams.get("create") === "1");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [taskDraft, setTaskDraft] = useState({
    projectId: "",
    title: "",
    dueDate: "",
    priority: "medium" as TaskPriority,
    taskType: "task" as TaskType,
    milestoneId: "",
    assigneeIds: [] as string[],
  });
  const [taskMembers, setTaskMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [taskMilestones, setTaskMilestones] = useState<MilestoneResponse[]>([]);
  const [isLoadingTaskOptions, setIsLoadingTaskOptions] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [taskCreateError, setTaskCreateError] = useState<string | null>(null);
  const [isCreatingTask, setIsCreatingTask] = useState(false);

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
    if (!token) return;
    setIsLoadingPlan(true);
    setPlanError(null);
    listProjects(token)
      .then(async (projectData) => {
        const taskGroups = await Promise.all(
          projectData.map((project) => listProjectTasks(token, project.id)),
        );
        setProjects(projectData);
        setWeeklyTasks(
          taskGroups.flat().filter((task) => task.parent_task_id === null),
        );
      })
      .catch((err) =>
        setPlanError(err instanceof Error ? err.message : "Failed to load the weekly plan"),
      )
      .finally(() => setIsLoadingPlan(false));
  }, [token]);

  useEffect(() => {
    setShowCreateForm(searchParams.get("create") === "1");
  }, [searchParams]);

  useEffect(() => {
    if (!token || !showTaskModal || !taskDraft.projectId) {
      setTaskMembers([]);
      setTaskMilestones([]);
      return;
    }
    let cancelled = false;
    setIsLoadingTaskOptions(true);
    Promise.all([
      listProjectMembers(token, taskDraft.projectId),
      listMilestones(token, taskDraft.projectId),
    ])
      .then(([members, milestones]) => {
        if (cancelled) return;
        setTaskMembers(members);
        setTaskMilestones(milestones);
      })
      .catch((err) => {
        if (!cancelled) {
          setTaskCreateError(err instanceof Error ? err.message : "Failed to load Task options");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingTaskOptions(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, showTaskModal, taskDraft.projectId]);

  function closeCreateForm() {
    if (isCreating) return;
    setShowCreateForm(false);
    setFormError(null);
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

  async function handleMoveTask(taskId: string, dueDate: string) {
    if (!token) return;
    const previous = weeklyTasks.find((task) => task.id === taskId);
    if (!previous || previous.due_date === dueDate) return;
    setPlanError(null);
    setWeeklyTasks((current) =>
      current.map((task) => task.id === taskId ? { ...task, due_date: dueDate } : task),
    );
    try {
      const updated = await updateTask(token, taskId, { due_date: dueDate });
      setWeeklyTasks((current) =>
        current.map((task) => task.id === taskId ? updated : task),
      );
    } catch (err) {
      setWeeklyTasks((current) =>
        current.map((task) => task.id === taskId ? previous : task),
      );
      setPlanError(err instanceof Error ? err.message : "Failed to reschedule the task");
    }
  }

  async function handleChangeTaskStatus(taskId: string, status: TaskStatus) {
    if (!token) return;
    const previous = weeklyTasks.find((task) => task.id === taskId);
    if (!previous || previous.status === status) return;
    setPlanError(null);
    setWeeklyTasks((current) =>
      current.map((task) => task.id === taskId ? { ...task, status } : task),
    );
    try {
      const updated = await updateTaskStatus(token, taskId, status);
      setWeeklyTasks((current) =>
        current.map((task) => task.id === taskId ? updated : task),
      );
    } catch (err) {
      setWeeklyTasks((current) =>
        current.map((task) => task.id === taskId ? previous : task),
      );
      setPlanError(err instanceof Error ? err.message : "Failed to change Task status");
    }
  }

  function openTaskModal(dueDate: string) {
    setTaskDraft({
      projectId: projects[0]?.id ?? "",
      title: "",
      dueDate,
      priority: "medium",
      taskType: "task",
      milestoneId: "",
      assigneeIds: [],
    });
    setTaskCreateError(null);
    setShowTaskModal(true);
  }

  function closeTaskModal() {
    if (isCreatingTask) return;
    setShowTaskModal(false);
    setTaskCreateError(null);
  }

  async function handleCreateTask(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !taskDraft.projectId || !taskDraft.title.trim()) return;
    setIsCreatingTask(true);
    setTaskCreateError(null);
    try {
      const created = await createTask(token, taskDraft.projectId, {
        title: taskDraft.title.trim(),
        due_date: taskDraft.dueDate,
        priority: taskDraft.priority,
        task_type: taskDraft.taskType,
        milestone_id: taskDraft.milestoneId || null,
        assignee_ids: taskDraft.assigneeIds,
      });
      setWeeklyTasks((current) => [...current, created]);
      setShowTaskModal(false);
    } catch (err) {
      setTaskCreateError(err instanceof Error ? err.message : "Failed to create Task");
    } finally {
      setIsCreatingTask(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-[100rem] space-y-6 p-6">
        <h1 className="text-2xl font-semibold text-slate-100">Home</h1>

        {planError && (
          <p role="alert" className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {planError}
          </p>
        )}
        {isLoadingPlan ? (
          <div className="h-80 animate-pulse rounded-lg bg-ink-900" />
        ) : (
          <WeeklyPlanBoard
            tasks={weeklyTasks}
            projects={projects}
            onMoveTask={handleMoveTask}
            onCreateTask={openTaskModal}
            onChangeStatus={handleChangeTaskStatus}
          />
        )}

        <div className="flex gap-6">
          <div className="min-w-0 flex-1 space-y-4">
            <AskBox />

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
              <ul className="divide-y divide-ink-800 rounded-md border border-ink-800 bg-ink-900">
                {activity.map((item) => (
                  <li key={item.id} className="px-4 py-3">
                    <Link
                      to={`/projects/${item.project_id}`}
                      className="font-medium text-slate-100 transition-colors hover:text-ember-400"
                    >
                      {item.project_name}
                    </Link>
                    <p className="mt-0.5 text-sm text-slate-400">{describeAction(item.action)}</p>
                    <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-500">
                      <span className="h-1.5 w-1.5 rounded-full bg-ember-500" />
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
      </div>

      {showCreateForm && (
        <Modal title="New project" onClose={closeCreateForm}>
          <form onSubmit={handleCreate} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Project name</span>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoFocus
                required
                className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={3}
                className="w-full rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
            </label>
            {formError && <p className="text-sm text-red-400">{formError}</p>}
            <ModalActions>
              <button
                type="button"
                onClick={closeCreateForm}
                disabled={isCreating}
                className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreating || !name.trim()}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {isCreating ? "Creating..." : "Create project"}
              </button>
            </ModalActions>
          </form>
        </Modal>
      )}

      {showTaskModal && (
        <Modal title="New Task" onClose={closeTaskModal}>
          <form onSubmit={handleCreateTask} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Project</span>
              <select
                value={taskDraft.projectId}
                onChange={(event) => setTaskDraft((current) => ({
                  ...current,
                  projectId: event.target.value,
                  milestoneId: "",
                  assigneeIds: [],
                }))}
                required
                className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
              >
                <option value="" disabled>Select a project</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Milestone</span>
              <select
                aria-label="Milestone"
                value={taskDraft.milestoneId}
                onChange={(event) => setTaskDraft((current) => ({ ...current, milestoneId: event.target.value }))}
                disabled={isLoadingTaskOptions}
                className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500 disabled:opacity-50"
              >
                <option value="">No milestone</option>
                {taskMilestones.map((milestone) => <option key={milestone.id} value={milestone.id}>{milestone.title}</option>)}
              </select>
            </label>
            <AssigneeMultiSelect
              members={taskMembers}
              selectedIds={taskDraft.assigneeIds}
              onChange={(assigneeIds) => setTaskDraft((current) => ({ ...current, assigneeIds }))}
            />
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Title</span>
              <input
                value={taskDraft.title}
                onChange={(event) => setTaskDraft((current) => ({ ...current, title: event.target.value }))}
                autoFocus
                required
                className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Due date</span>
              <input
                type="date"
                value={taskDraft.dueDate}
                onChange={(event) => setTaskDraft((current) => ({ ...current, dueDate: event.target.value }))}
                required
                className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Priority</span>
                <select
                  value={taskDraft.priority}
                  onChange={(event) => setTaskDraft((current) => ({ ...current, priority: event.target.value as TaskPriority }))}
                  className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
                >
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option>
                </select>
              </label>
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Type</span>
                <select
                  value={taskDraft.taskType}
                  onChange={(event) => setTaskDraft((current) => ({ ...current, taskType: event.target.value as TaskType }))}
                  className="w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-ember-500"
                >
                  <option value="task">Task</option><option value="bug">Bug</option><option value="improvement">Improvement</option><option value="incident">Incident</option>
                </select>
              </label>
            </div>
            {taskCreateError && <p className="text-sm text-red-400">{taskCreateError}</p>}
            <ModalActions>
              <button
                type="button"
                onClick={closeTaskModal}
                disabled={isCreatingTask}
                className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreatingTask || !taskDraft.projectId || !taskDraft.title.trim()}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {isCreatingTask ? "Creating..." : "Create Task"}
              </button>
            </ModalActions>
          </form>
        </Modal>
      )}
    </AppShell>
  );
}
