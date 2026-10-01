import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { ProjectMemberDetailResponse } from "../api/client";
import type {
  TaskPriority,
  TaskResponse,
  TaskStatus,
  KanbanColumnResponse,
} from "../api/client_tasks";
import { PRIORITY_COLORS, PriorityScoreChip, STATUS_LABELS } from "./TaskBadges";
import { PlusIcon, TrashIcon } from "./icons";
import Modal, { ModalActions } from "./Modal";

const ALL_STATUSES: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];
const PRIORITY_OPTIONS: TaskPriority[] = ["low", "medium", "high", "urgent"];

// Highest Priority Score first, so the card that most needs attention is
// always the top one in its column. Cards with no score (done, or no
// due_date) sort last regardless of direction - there's nothing to rank
// them by. Ties (e.g. two cards both scored 10 while overdue) fall back to
// whichever has fewer days left until its due_date, so the more time-
// critical of the two still surfaces above the other.
function compareCards(a: TaskResponse, b: TaskResponse): number {
  const scoreA = a.priority_score;
  const scoreB = b.priority_score;
  if (scoreA === null && scoreB === null) return 0;
  if (scoreA === null) return 1;
  if (scoreB === null) return -1;
  if (scoreA !== scoreB) return scoreB - scoreA;

  const dueA = a.due_date;
  const dueB = b.due_date;
  if (dueA === null && dueB === null) return 0;
  if (dueA === null) return 1;
  if (dueB === null) return -1;
  return dueA.localeCompare(dueB);
}

function KanbanCard({
  task,
  projectId,
  assigneeName,
  members,
  onUpdateTask,
  milestoneName,
}: {
  task: TaskResponse;
  projectId: string;
  assigneeName: string | null;
  members: ProjectMemberDetailResponse[];
  onUpdateTask: (taskId: string, fields: { assignee_id?: string | null; priority?: TaskPriority }) => void;
  milestoneName: string | null;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`cursor-grab space-y-1 rounded-md border border-ink-700 bg-ink-800 p-2 text-sm active:cursor-grabbing ${
        isDragging ? "z-10 opacity-70" : ""
      }`}
    >
      <Link
        to={`/projects/${projectId}/tasks/${task.id}`}
        onClick={(e) => isDragging && e.preventDefault()}
        className="text-slate-100 hover:text-ember-400"
      >
        {task.title}
      </Link>
      <div
        className="flex items-center gap-1"
        // The card itself is draggable; stop these controls from starting a
        // drag so clicking a badge opens its selector normally.
        onPointerDown={(event) => event.stopPropagation()}
      >
        <select
          value={task.priority}
          onChange={(event) =>
            onUpdateTask(task.id, { priority: event.target.value as TaskPriority })
          }
          aria-label={`Priority for ${task.title}`}
          title="Change priority"
          className={`cursor-pointer appearance-none rounded-full border-0 px-2 py-0.5 text-xs font-medium outline-none focus:ring-1 focus:ring-ember-500 ${PRIORITY_COLORS[task.priority]}`}
        >
          {PRIORITY_OPTIONS.map((priority) => (
            <option key={priority} value={priority} className="bg-ink-900 text-slate-200">
              {priority}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500">{task.task_type}</span>
        <span className="ml-auto flex min-w-0 items-center gap-1">
          {task.priority_score !== null && <PriorityScoreChip score={task.priority_score} />}
        <select
          value={task.assignee_id ?? ""}
          onChange={(event) => onUpdateTask(task.id, { assignee_id: event.target.value || null })}
          aria-label={`Responsible person for ${task.title}`}
          title={assigneeName ?? "Unassigned"}
          className="max-w-24 cursor-pointer appearance-none truncate rounded-full border-0 bg-ink-700 px-2 py-0.5 text-xs font-medium text-slate-300 outline-none focus:ring-1 focus:ring-ember-500"
        >
          <option value="" className="bg-ink-900 text-slate-200">Unassigned</option>
          {members.map((member) => (
            <option
              key={member.user_id}
              value={member.user_id}
              className="bg-ink-900 text-slate-200"
            >
              {member.full_name}
            </option>
          ))}
        </select>
        </span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span className="truncate">{milestoneName ? `Milestone: ${milestoneName}` : "No milestone"}</span>
        <span>Subtasks: {task.subtasks_completed} / {task.subtasks_total}</span>
      </div>
    </div>
  );
}

function StatusCheckboxes({
  selected,
  onChange,
}: {
  selected: TaskStatus[];
  onChange: (statuses: TaskStatus[]) => void;
}) {
  function toggle(status: TaskStatus) {
    onChange(
      selected.includes(status)
        ? selected.filter((s) => s !== status)
        : [...selected, status],
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {ALL_STATUSES.map((status) => (
        <label key={status} className="flex items-center gap-1 text-xs text-slate-400">
          <input
            type="checkbox"
            checked={selected.includes(status)}
            onChange={() => toggle(status)}
            className="accent-ember-500"
          />
          {STATUS_LABELS[status]}
        </label>
      ))}
    </div>
  );
}

function KanbanColumnView({
  column,
  tasks,
  projectId,
  assigneeNameById,
  milestoneNameById,
  members,
  onUpdateTask,
  onRenameColumn,
  onDeleteColumn,
}: {
  column: KanbanColumnResponse;
  tasks: TaskResponse[];
  projectId: string;
  assigneeNameById: Map<string, string>;
  milestoneNameById: Map<string, string>;
  members: ProjectMemberDetailResponse[];
  onUpdateTask: (taskId: string, fields: { assignee_id?: string | null; priority?: TaskPriority }) => void;
  onRenameColumn: (columnId: string, name: string, mapsToStatuses: TaskStatus[]) => void;
  onDeleteColumn: (columnId: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(column.name);
  const [statuses, setStatuses] = useState<TaskStatus[]>(column.maps_to_statuses);

  function handleSave() {
    if (!name.trim()) return;
    onRenameColumn(column.id, name.trim(), statuses);
    setIsEditing(false);
  }

  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 flex-shrink-0 flex-col rounded-md border p-2 ${
        isOver ? "border-ember-500 bg-ember-500/5" : "border-ink-800 bg-ink-900"
      }`}
    >
      {isEditing ? (
        <div className="mb-2 space-y-2 rounded-md border border-ink-700 bg-ink-850 p-2">
          <input
            autoFocus
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 outline-none focus:border-ember-500"
          />
          <StatusCheckboxes selected={statuses} onChange={setStatuses} />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="rounded-md bg-ember-500 px-2 py-1 text-xs font-medium text-white hover:bg-ember-600"
            >
              Save
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="rounded-md border border-ink-700 px-2 py-1 text-xs text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <h3 className="group mb-2 flex items-center justify-between px-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          <button onClick={() => setIsEditing(true)} className="truncate hover:text-slate-200">
            {column.name}
          </button>
          <span className="flex items-center gap-1">
            <span className="rounded-full bg-ink-800 px-1.5 py-0.5 text-slate-500">
              {tasks.length}
            </span>
            <button
              onClick={() => onDeleteColumn(column.id)}
              title="Delete column"
              className="text-slate-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
            >
              <TrashIcon className="h-3.5 w-3.5" />
            </button>
          </span>
        </h3>
      )}
      <div className="min-h-16 flex-1 space-y-3">
        {tasks.sort(compareCards).map((task) => <KanbanCard
          key={task.id} task={task} projectId={projectId}
          assigneeName={task.assignee_id ? (assigneeNameById.get(task.assignee_id) ?? null) : null}
          members={members} onUpdateTask={onUpdateTask}
          milestoneName={task.milestone_id ? milestoneNameById.get(task.milestone_id) ?? null : null}
        />)}
      </div>
    </div>
  );
}

function NewColumnForm({
  onCreate,
}: {
  onCreate: (name: string, mapsToStatuses: TaskStatus[]) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [statuses, setStatuses] = useState<TaskStatus[]>([]);

  function handleCreate() {
    if (!name.trim()) return;
    onCreate(name.trim(), statuses);
    setName("");
    setStatuses([]);
    setShowForm(false);
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="flex h-fit w-64 flex-shrink-0 items-center justify-center gap-1 rounded-md border border-dashed border-ink-700 p-3 text-sm text-slate-500 transition-colors hover:border-ink-600 hover:text-slate-300"
      >
        <PlusIcon className="h-4 w-4" />
        New column
      </button>
    );
  }

  return (
    <div className="w-64 flex-shrink-0 space-y-2 rounded-md border border-ink-700 bg-ink-900 p-2">
      <input
        autoFocus
        type="text"
        placeholder="Column name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-md border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-100 outline-none focus:border-ember-500"
      />
      <StatusCheckboxes selected={statuses} onChange={setStatuses} />
      <div className="flex gap-2">
        <button
          onClick={handleCreate}
          className="rounded-md bg-ember-500 px-2 py-1 text-xs font-medium text-white hover:bg-ember-600"
        >
          Create
        </button>
        <button
          onClick={() => setShowForm(false)}
          className="rounded-md border border-ink-700 px-2 py-1 text-xs text-slate-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function KanbanBoard({
  columns,
  tasks,
  members,
  projectId,
  onMoveTask,
  onUpdateTask,
  onCreateColumn,
  onRenameColumn,
  onDeleteColumn,
  milestoneNameById = new Map(),
}: {
  columns: KanbanColumnResponse[];
  tasks: TaskResponse[];
  members: ProjectMemberDetailResponse[];
  projectId: string;
  onMoveTask: (taskId: string, status: TaskStatus) => void;
  onUpdateTask: (taskId: string, fields: { assignee_id?: string | null; priority?: TaskPriority }) => void;
  onCreateColumn: (name: string, mapsToStatuses: TaskStatus[]) => void;
  onRenameColumn: (columnId: string, name: string, mapsToStatuses: TaskStatus[]) => void;
  onDeleteColumn: (columnId: string) => void;
  milestoneNameById?: Map<string, string>;
}) {
  const [pendingMove, setPendingMove] = useState<{ taskId: string; status: TaskStatus } | null>(
    null,
  );
  const assigneeNameById = useMemo(
    () => new Map(members.map((member) => [member.user_id, member.full_name])),
    [members],
  );
  const boardTasks = useMemo(() => tasks.filter((task) => task.parent_task_id === null), [tasks]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const taskId = String(active.id);
    const targetColumn = columns.find((c) => c.id === over.id);
    if (!targetColumn || targetColumn.maps_to_statuses.length === 0) return;
    const targetStatus = targetColumn.maps_to_statuses[0];
    const task = boardTasks.find((i) => i.id === taskId);
    if (!task || task.status === targetStatus) return;
    if (targetStatus === "done") {
      setPendingMove({ taskId, status: targetStatus });
      return;
    }
    onMoveTask(taskId, targetStatus);
  }

  const pendingTask = pendingMove ? boardTasks.find((i) => i.id === pendingMove.taskId) : null;

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {columns.map((column) => (
          <KanbanColumnView
            key={column.id}
            column={column}
            tasks={boardTasks
              .filter((task) => column.maps_to_statuses.includes(task.status))
              .sort(compareCards)}
            projectId={projectId}
            assigneeNameById={assigneeNameById}
            milestoneNameById={milestoneNameById}
            members={members}
            onUpdateTask={onUpdateTask}
            onRenameColumn={onRenameColumn}
            onDeleteColumn={onDeleteColumn}
          />
        ))}
        <NewColumnForm onCreate={onCreateColumn} />
      </div>

      {pendingMove && (
        <Modal title="Complete this Task?" onClose={() => setPendingMove(null)}>
          <p className="text-sm text-slate-400">
            Marking{" "}
            <span className="text-slate-200">{pendingTask?.title ?? "this task"}</span> as done
            will be completed only if all of its Subtasks are done.
          </p>
          <ModalActions>
            <button
              onClick={() => setPendingMove(null)}
              className="rounded-md border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                onMoveTask(pendingMove.taskId, pendingMove.status);
                setPendingMove(null);
              }}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Complete Task
            </button>
          </ModalActions>
        </Modal>
      )}
    </DndContext>
  );
}
