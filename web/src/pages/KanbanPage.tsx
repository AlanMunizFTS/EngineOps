import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import {
  getProject,
  listProjectMembers,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import {
  createTask,
  createKanbanBoard,
  createKanbanColumn,
  deleteKanbanBoard,
  deleteKanbanColumn,
  listKanbanBoards,
  listMilestones,
  listProjectTasks,
  renameKanbanBoard,
  updateTask,
  updateTaskStatus,
  type TaskPriority,
  type TaskType,
  updateKanbanColumn,
  type TaskResponse,
  type TaskStatus,
  type KanbanBoardResponse,
  type MilestoneResponse,
} from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import DailyRepeatField from "../components/DailyRepeatField";
import KanbanBoard from "../components/KanbanBoard";
import ProjectTabs from "../components/ProjectTabs";
import { PlusIcon, TrashIcon } from "../components/icons";
import Modal, { ModalActions } from "../components/Modal";

const UNASSIGNED_FILTER_VALUE = "__unassigned__";
const INPUT_CLASS = "w-full rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-ember-500";

export default function KanbanPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [boards, setBoards] = useState<KanbanBoardResponse[]>([]);
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [milestones, setMilestones] = useState<MilestoneResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [showNewBoard, setShowNewBoard] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTask, setNewTask] = useState({ title: "", description: "", status: "backlog" as TaskStatus, priority: "medium" as TaskPriority, taskType: "task" as TaskType, startDate: "", dueDate: "", repeatDaily: false });
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [taskCreateError, setTaskCreateError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, boardData, taskData, memberData, milestoneData] = await Promise.all([
        getProject(token, projectId),
        listKanbanBoards(token, projectId),
        listProjectTasks(token, projectId),
        listProjectMembers(token, projectId),
        listMilestones(token, projectId),
      ]);
      setProject(projectData);
      setBoards(boardData);
      setTasks(taskData.filter((task) => task.parent_task_id === null));
      setMembers(memberData);
      setMilestones(milestoneData);
      setActiveBoardId((current) =>
        current && boardData.some((b) => b.id === current) ? current : (boardData[0]?.id ?? null),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load kanban board");
    }
  }

  const filteredTasks = useMemo(() => {
    if (!assigneeFilter) return tasks;
    return tasks.filter((task) =>
      assigneeFilter === UNASSIGNED_FILTER_VALUE
        ? task.assignee_ids.length === 0
        : task.assignee_ids.includes(assigneeFilter),
    );
  }, [tasks, assigneeFilter]);

  async function handleMoveTask(taskId: string, status: TaskStatus) {
    if (!token) return;
    const previous = tasks;
    setTasks((current) =>
      current.map((task) => (task.id === taskId ? { ...task, status } : task)),
    );
    try {
      await updateTaskStatus(token, taskId, status);
    } catch (err) {
      setTasks(previous);
      setError(err instanceof Error ? err.message : "Failed to move task");
    }
  }

  async function handleUpdateTask(
    taskId: string,
    fields: { assignee_id?: string | null; priority?: TaskPriority },
  ) {
    if (!token) return;
    const task = tasks.find((candidate) => candidate.id === taskId);
    if (!task) return;
    const previous = tasks;
    setTasks((current) =>
      current.map((candidate) => (candidate.id === taskId ? { ...candidate, ...fields } : candidate)),
    );
    try {
      const updated = await updateTask(token, taskId, {
        priority: fields.priority ?? task.priority,
        assignee_id: "assignee_id" in fields ? (fields.assignee_id ?? null) : task.assignee_id,
      });
      setTasks((current) => current.map((candidate) => (candidate.id === taskId ? updated : candidate)));
    } catch (err) {
      setTasks(previous);
      setError(err instanceof Error ? err.message : "Failed to update task");
    }
  }

  async function handleCreateBoard() {
    if (!token || !projectId || !newBoardName.trim()) return;
    try {
      const board = await createKanbanBoard(token, projectId, newBoardName.trim());
      setNewBoardName("");
      setShowNewBoard(false);
      setBoards((current) => [...current, board]);
      setActiveBoardId(board.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create board");
    }
  }

  function openNewTask() {
    const defaultStatus = activeBoard?.columns.find((column) => column.maps_to_statuses.length > 0)?.maps_to_statuses[0] ?? "backlog";
    setNewTask({ title: "", description: "", status: defaultStatus, priority: "medium", taskType: "task", startDate: "", dueDate: "", repeatDaily: false });
    setTaskCreateError(null);
    setShowNewTask(true);
  }

  function closeNewTask() {
    if (isCreatingTask) return;
    setShowNewTask(false);
    setTaskCreateError(null);
  }

  async function handleCreateTask(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !projectId || !newTask.title.trim()) return;
    if (newTask.startDate && newTask.dueDate && newTask.dueDate < newTask.startDate) {
      setTaskCreateError("Due date cannot be before the start date.");
      return;
    }
    setIsCreatingTask(true);
    setTaskCreateError(null);
    try {
      const created = await createTask(token, projectId, {
        title: newTask.title.trim(),
        description: newTask.description.trim() || null,
        status: newTask.status,
        priority: newTask.priority,
        task_type: newTask.taskType,
        start_date: newTask.startDate || null,
        due_date: newTask.dueDate || null,
        repeat_daily: newTask.repeatDaily,
      });
      setTasks((current) => [created, ...current]);
      setShowNewTask(false);
    } catch (err) {
      setTaskCreateError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setIsCreatingTask(false);
    }
  }

  async function handleRenameBoard(boardId: string, name: string) {
    if (!token) return;
    try {
      const updated = await renameKanbanBoard(token, boardId, name);
      setBoards((current) => current.map((b) => (b.id === boardId ? updated : b)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename board");
    }
  }

  async function handleDeleteBoard(boardId: string) {
    if (!token) return;
    if (!window.confirm("Delete this board? Its columns will be removed too.")) return;
    try {
      await deleteKanbanBoard(token, boardId);
      setBoards((current) => {
        const remaining = current.filter((b) => b.id !== boardId);
        setActiveBoardId(remaining[0]?.id ?? null);
        return remaining;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete board");
    }
  }

  async function handleCreateColumn(name: string, mapsToStatuses: TaskStatus[]) {
    if (!token || !activeBoardId) return;
    try {
      const column = await createKanbanColumn(token, activeBoardId, name, mapsToStatuses);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId ? { ...b, columns: [...b.columns, column] } : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create column");
    }
  }

  async function handleRenameColumn(columnId: string, name: string, mapsToStatuses: TaskStatus[]) {
    if (!token || !activeBoardId) return;
    try {
      const updated = await updateKanbanColumn(token, columnId, name, mapsToStatuses);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId
            ? { ...b, columns: b.columns.map((c) => (c.id === columnId ? updated : c)) }
            : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update column");
    }
  }

  async function handleDeleteColumn(columnId: string) {
    if (!token || !activeBoardId) return;
    if (!window.confirm("Delete this column?")) return;
    try {
      await deleteKanbanColumn(token, columnId);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId
            ? { ...b, columns: b.columns.filter((c) => c.id !== columnId) }
            : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete column");
    }
  }

  const activeBoard = boards.find((b) => b.id === activeBoardId) ?? null;

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="p-6">
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={openNewTask}
            className="flex items-center gap-1 rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-ember-600"
          >
            <PlusIcon className="h-3.5 w-3.5" />
            New task
          </button>
          {boards.map((board) => (
            <div key={board.id} className="group flex items-center">
              <button
                onClick={() => setActiveBoardId(board.id)}
                onDoubleClick={() => {
                  const name = window.prompt("Rename board", board.name);
                  if (name && name.trim() && name.trim() !== board.name) {
                    void handleRenameBoard(board.id, name.trim());
                  }
                }}
                title="Double-click to rename"
                className={`rounded-l-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                  board.id === activeBoardId
                    ? "border-ember-500 bg-ember-500/10 text-ember-400"
                    : "border-ink-700 bg-ink-850 text-slate-300 hover:border-ink-600"
                }`}
              >
                {board.name}
              </button>
              {boards.length > 1 && (
                <button
                  onClick={() => handleDeleteBoard(board.id)}
                  title="Delete board"
                  className={`rounded-r-md border border-l-0 px-1.5 py-1.5 text-slate-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100 ${
                    board.id === activeBoardId
                      ? "border-ember-500 bg-ember-500/10"
                      : "border-ink-700 bg-ink-850"
                  }`}
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}

          {showNewBoard ? (
            <div className="flex items-center gap-1">
              <input
                autoFocus
                type="text"
                placeholder="Board name"
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateBoard()}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateBoard}
                className="rounded-md bg-ember-500 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowNewBoard(true)}
              className="flex items-center gap-1 rounded-md border border-dashed border-ink-700 px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:border-ink-600 hover:text-slate-300"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              New board
            </button>
          )}

          <select
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            className="ml-auto rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1.5 text-sm text-slate-300 outline-none focus:border-ember-500"
          >
            <option value="">All assignees</option>
            <option value={UNASSIGNED_FILTER_VALUE}>Unassigned</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.full_name}
              </option>
            ))}
          </select>
        </div>

        {activeBoard ? (
          <KanbanBoard
            columns={activeBoard.columns}
            tasks={filteredTasks}
            members={members}
            projectId={project.id}
            onMoveTask={handleMoveTask}
            onUpdateTask={handleUpdateTask}
            onCreateColumn={handleCreateColumn}
            onRenameColumn={handleRenameColumn}
            onDeleteColumn={handleDeleteColumn}
            milestoneNameById={new Map(milestones.map((milestone) => [milestone.id, milestone.title]))}
          />
        ) : (
          <p className="text-sm text-slate-500">No boards yet.</p>
        )}
      </div>

      {showNewTask && (
        <Modal title="New task" onClose={closeNewTask}>
          <form onSubmit={handleCreateTask} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Title</span>
              <input
                autoFocus
                value={newTask.title}
                onChange={(event) => setNewTask((current) => ({ ...current, title: event.target.value }))}
                placeholder="What needs to be done?"
                maxLength={255}
                required
                className={INPUT_CLASS}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Description <span className="font-normal text-slate-600">(optional)</span></span>
              <textarea value={newTask.description} onChange={(event) => setNewTask((current) => ({ ...current, description: event.target.value }))} rows={3} className={INPUT_CLASS} />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Status</span>
                <select value={newTask.status} onChange={(event) => setNewTask((current) => ({ ...current, status: event.target.value as TaskStatus }))} className={INPUT_CLASS}>
                  <option value="backlog">Backlog</option><option value="todo">To do</option><option value="in_progress">In progress</option><option value="in_review">In review</option><option value="done">Done</option>
                </select>
              </label>
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Priority</span>
                <select value={newTask.priority} onChange={(event) => setNewTask((current) => ({ ...current, priority: event.target.value as TaskPriority }))} className={INPUT_CLASS}>
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option>
                </select>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Type</span>
                <select value={newTask.taskType} onChange={(event) => setNewTask((current) => ({ ...current, taskType: event.target.value as TaskType }))} className={INPUT_CLASS}>
                  <option value="task">Task</option><option value="bug">Bug</option><option value="improvement">Improvement</option><option value="incident">Incident</option>
                </select>
              </label>
              <div />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Start date</span>
                <input type="date" value={newTask.startDate} onChange={(event) => setNewTask((current) => ({ ...current, startDate: event.target.value }))} className={INPUT_CLASS} />
              </label>
              <label>
                <span className="mb-1 block text-xs font-medium text-slate-400">Due date</span>
                <input type="date" value={newTask.dueDate} min={newTask.startDate || undefined} onChange={(event) => setNewTask((current) => ({ ...current, dueDate: event.target.value }))} className={INPUT_CLASS} />
              </label>
            </div>
            <DailyRepeatField checked={newTask.repeatDaily} onChange={(repeatDaily) => setNewTask((current) => ({ ...current, repeatDaily }))} />
            {taskCreateError && <p role="alert" className="text-sm text-red-400">{taskCreateError}</p>}
            <ModalActions>
              <button type="button" onClick={closeNewTask} disabled={isCreatingTask} className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 hover:border-ink-600 disabled:opacity-50">Cancel</button>
              <button type="submit" disabled={isCreatingTask || !newTask.title.trim()} className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-ember-600 disabled:cursor-not-allowed disabled:opacity-50">{isCreatingTask ? "Creating..." : "Create task"}</button>
            </ModalActions>
          </form>
        </Modal>
      )}
    </AppShell>
  );
}
