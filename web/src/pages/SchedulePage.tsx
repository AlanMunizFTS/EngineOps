import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, UIEvent, WheelEvent } from "react";
import { Link, useParams } from "react-router-dom";

import {
  downloadProjectExport,
  getProject,
  listProjectMembers,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import {
  createTask,
  createSubtask,
  updateTask,
  updateTaskStatus,
  updateTaskParent,
  listProjectTasks,
  type TaskPriority,
  type TaskResponse,
  type TaskStatus,
} from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import { DownloadIcon, PlusIcon } from "../components/icons";
import { PRIORITY_COLORS, PriorityScoreChip } from "../components/TaskBadges";
import Modal, { ModalActions } from "../components/Modal";
import ProjectTabs from "../components/ProjectTabs";

const DAY_WIDTH = 32;
// Month band, week band, day letter/number, per-column filters.
const HEADER_ROWS = 4;
const ROW_HEIGHT = 32;
const DAY_LETTERS = ["S", "M", "T", "W", "T", "F", "S"]; // Date#getDay(): 0=Sun..6=Sat
const STATUS_OPTIONS: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];
const PRIORITY_OPTIONS: TaskPriority[] = ["low", "medium", "high", "urgent"];

const STICKY_COLUMNS = [
  { key: "index", label: "#", width: 56 },
  { key: "activity", label: "Activity", width: 220 },
  { key: "responsible", label: "Responsible", width: 120 },
  { key: "start", label: "Start", width: 118 },
  { key: "due", label: "Due", width: 118 },
  { key: "status", label: "Status", width: 110 },
  { key: "priority", label: "Priority", width: 90 },
  { key: "score", label: "Score", width: 56 },
];
// Every column except "#" and "Activity" folds away when the info pane is
// collapsed - those two are the minimum needed to still identify a row.
const COLLAPSIBLE_COLUMN_KEYS = new Set(
  STICKY_COLUMNS.filter((col) => col.key !== "index" && col.key !== "activity").map(
    (col) => col.key,
  ),
);

// Dates from the API are plain "YYYY-MM-DD" calendar dates with no
// timezone. `new Date("2026-07-16")` parses that as UTC midnight, which
// renders as the previous day in any timezone behind UTC - so every date
// here is handled as a local calendar date instead, never round-tripped
// through UTC parsing/serializing.
function parseLocalDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function isoDate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}

function startOfWeek(d: Date): Date {
  const day = d.getDay();
  return addDays(d, day === 0 ? -6 : 1 - day);
}

function endOfWeek(d: Date): Date {
  return addDays(startOfWeek(d), 6);
}

function weekNumber(d: Date): number {
  const yearStart = new Date(d.getFullYear(), 0, 1);
  const diffDays = Math.floor((d.getTime() - yearStart.getTime()) / 86_400_000);
  return Math.ceil((diffDays + yearStart.getDay() + 1) / 7);
}

interface BarSegment {
  startIso: string;
  endIso: string;
  color: string;
}

function nextIso(iso: string): string {
  return isoDate(addDays(parseLocalDate(iso), 1));
}

function computeBarSegments(task: TaskResponse, todayIso: string): BarSegment[] {
  const dueIso = task.due_date;
  if (!dueIso) return [];
  const startIso = task.start_date ?? dueIso;

  if (!task.closed_at_date) {
    const isLate = task.schedule_status === "late";
    // A late, still-open activity has no closed_at to bound its bar, so it
    // must keep stretching past due_date up to today - otherwise the red
    // "late" bar looks like it stopped at due_date instead of still being
    // overdue right now.
    const endIso = isLate && todayIso > dueIso ? todayIso : dueIso;
    const color = isLate ? "bg-red-500" : "bg-sky-500";
    return [{ startIso, endIso, color }];
  }

  // `closed_at_date` is already the business-timezone (UTC-6) calendar day,
  // computed server-side (`domain/scheduling.to_business_date`) - comparing
  // the raw `closed_at` timestamp's own UTC date here instead would be
  // wrong for roughly six hours every evening (18:00-23:59 UTC-6, when the
  // UTC calendar day has already rolled to tomorrow).
  const closedIso = task.closed_at_date;
  if (closedIso <= dueIso) {
    const segments: BarSegment[] = [{ startIso, endIso: closedIso, color: "bg-sky-500" }];
    if (closedIso < dueIso) {
      segments.push({ startIso: nextIso(closedIso), endIso: dueIso, color: "bg-emerald-500" });
    }
    return segments;
  }

  return [
    { startIso, endIso: dueIso, color: "bg-sky-500" },
    { startIso: nextIso(dueIso), endIso: closedIso, color: "bg-red-500" },
  ];
}

interface EffectiveRange {
  start: string | null;
  due: string | null;
  isRollup: boolean;
}

/**
 * A Task's Gantt bar rolls up its direct Subtask dates. The domain allows
 * exactly one hierarchy level, so recursive traversal is intentionally absent.
 */
function buildEffectiveRanges(tasks: TaskResponse[]): Map<string, EffectiveRange> {
  const childrenByParent = new Map<string, TaskResponse[]>();
  for (const task of tasks) {
    if (task.parent_task_id) {
      const siblings = childrenByParent.get(task.parent_task_id) ?? [];
      siblings.push(task);
      childrenByParent.set(task.parent_task_id, siblings);
    }
  }

  const cache = new Map<string, EffectiveRange>();
  function resolve(task: TaskResponse): EffectiveRange {
    const cached = cache.get(task.id);
    if (cached) return cached;
    let start: string | null = null;
    let due: string | null = null;
    for (const child of childrenByParent.get(task.id) ?? []) {
      if (child.start_date && (!start || child.start_date < start)) start = child.start_date;
      if (child.due_date && (!due || child.due_date > due)) due = child.due_date;
    }

    const result: EffectiveRange =
      start !== null || due !== null
        ? { start, due, isRollup: true }
        : { start: task.start_date, due: task.due_date, isRollup: false };

    cache.set(task.id, result);
    return result;
  }

  for (const task of tasks) resolve(task);
  return cache;
}

interface ScheduleRow {
  task: TaskResponse;
  number: string;
  depth: number;
  hasChildren: boolean;
}

const PRIORITY_RANK: Record<TaskPriority, number> = { low: 1, medium: 2, high: 3, urgent: 4 };

type ScheduleSortKey = "entry" | "priority" | "score";
type ScheduleSortDirection = "asc" | "desc";

/**
 * Sorting stays scoped to each sibling group (roots among themselves,
 * children among their own siblings) rather than flattening the whole
 * tree - the numbering (1, 1.1, 1.2, ...) must still nest under a real
 * parent row, so "sort by priority" reorders who's 1.1 vs 1.2, not
 * whether a subtask can appear above its own parent.
 */
export function buildScheduleRows(
  tasks: TaskResponse[],
  collapsed: Set<string>,
  sortKey: ScheduleSortKey,
  sortDirection: ScheduleSortDirection,
): ScheduleRow[] {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  const childrenById = new Map<string, TaskResponse[]>();
  const roots: TaskResponse[] = [];
  for (const task of tasks) {
    if (task.parent_task_id && byId.has(task.parent_task_id)) {
      const siblings = childrenById.get(task.parent_task_id) ?? [];
      siblings.push(task);
      childrenById.set(task.parent_task_id, siblings);
    } else {
      roots.push(task);
    }
  }

  const dir = sortDirection === "asc" ? 1 : -1;
  // Root entry order follows created_at; sibling entry order follows
  // parent_assigned_at instead - when the task most recently became a
  // child of THIS parent, not when it was originally created - so
  // unlinking a child and re-linking it later moves it to the end of its
  // new siblings rather than pinning it to its original creation time.
  const entryKey = (task: TaskResponse, isRoot: boolean) =>
    isRoot ? task.created_at : (task.parent_assigned_at ?? task.created_at);
  const byEntry = (isRoot: boolean) => (a: TaskResponse, b: TaskResponse) =>
    dir * entryKey(a, isRoot).localeCompare(entryKey(b, isRoot));
  const byPriority = (isRoot: boolean) => (a: TaskResponse, b: TaskResponse) => {
    const diff = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    return diff !== 0 ? dir * diff : entryKey(a, isRoot).localeCompare(entryKey(b, isRoot));
  };
  // Tasks with no score (done, or no due_date) always sort last,
  // regardless of direction - there's nothing to rank them by.
  const byScore = (isRoot: boolean) => (a: TaskResponse, b: TaskResponse) => {
    const scoreA = a.priority_score;
    const scoreB = b.priority_score;
    if (scoreA === null && scoreB === null) {
      return entryKey(a, isRoot).localeCompare(entryKey(b, isRoot));
    }
    if (scoreA === null) return 1;
    if (scoreB === null) return -1;
    const diff = scoreA - scoreB;
    return diff !== 0 ? dir * diff : entryKey(a, isRoot).localeCompare(entryKey(b, isRoot));
  };
  const comparator = (isRoot: boolean) => {
    if (sortKey === "priority") return byPriority(isRoot);
    if (sortKey === "score") return byScore(isRoot);
    return byEntry(isRoot);
  };

  roots.sort(comparator(true));
  for (const siblings of childrenById.values()) siblings.sort(comparator(false));

  const rows: ScheduleRow[] = [];
  function visit(task: TaskResponse, number: string) {
    const children = childrenById.get(task.id) ?? [];
    rows.push({ task, number, depth: 0, hasChildren: children.length > 0 });
    if (collapsed.has(task.id)) return;
    children.forEach((child, i) => rows.push({ task: child, number: `${number}.${i + 1}`, depth: 1, hasChildren: false }));
  }
  roots.forEach((task, i) => visit(task, `${i + 1}`));
  return rows;
}

interface ScheduleFilters {
  activity: string;
  responsible: string;
  status: Set<TaskStatus>;
  priority: TaskPriority | "";
  dueToday: boolean;
}

const UNASSIGNED_FILTER_VALUE = "__unassigned__";

function matchesFilters(task: TaskResponse, filters: ScheduleFilters, todayIso: string): boolean {
  if (filters.activity.trim() && !task.title.toLowerCase().includes(filters.activity.trim().toLowerCase())) {
    return false;
  }
  if (filters.responsible) {
    if (filters.responsible === UNASSIGNED_FILTER_VALUE) {
      if (task.assignee_id !== null) return false;
    } else if (task.assignee_id !== filters.responsible) {
      return false;
    }
  }
  if (filters.status.size > 0 && !filters.status.has(task.status)) return false;
  if (filters.priority && task.priority !== filters.priority) return false;
  if (filters.dueToday) {
    // "Should theoretically be worked on today", regardless of priority:
    // not done, has a due date, and hasn't been scheduled to start in the
    // future. Includes overdue items - those need today's attention most.
    const isActiveToday =
      task.status !== "done" &&
      task.due_date !== null &&
      (task.start_date === null || task.start_date <= todayIso);
    if (!isActiveToday) return false;
  }
  return true;
}

// A filtered-in task keeps its whole ancestor chain visible too, so the
// tree structure/numbering stays intelligible instead of showing orphaned
// deeply-indented rows with no parent above them.
function computeFilterKeepSet(
  tasks: TaskResponse[],
  filters: ScheduleFilters,
  todayIso: string,
): Set<string> {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  const keep = new Set<string>();
  for (const task of tasks) {
    if (!matchesFilters(task, filters, todayIso)) continue;
    let current: TaskResponse | undefined = task;
    while (current && !keep.has(current.id)) {
      keep.add(current.id);
      current = current.parent_task_id ? byId.get(current.parent_task_id) : undefined;
    }
  }
  return keep;
}

function StatusFilterDropdown({
  selected,
  onChange,
}: {
  selected: Set<TaskStatus>;
  onChange: (next: Set<TaskStatus>) => void;
}) {
  const [open, setOpen] = useState(false);
  const label = selected.size === 0 ? "All" : `${selected.size} selected`;

  function toggle(status: TaskStatus) {
    const next = new Set(selected);
    if (next.has(status)) next.delete(status);
    else next.add(status);
    onChange(next);
  }

  return (
    <div
      className="relative w-full"
      tabIndex={-1}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full truncate rounded border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-left text-[11px] text-slate-300 outline-none focus:border-ember-500"
      >
        {label}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-1 w-40 rounded-md border border-ink-700 bg-ink-900 p-2 shadow-lg">
          {STATUS_OPTIONS.map((status) => (
            <label
              key={status}
              className="flex items-center gap-1.5 py-0.5 text-[11px] text-slate-300"
            >
              <input
                type="checkbox"
                checked={selected.has(status)}
                onChange={() => toggle(status)}
                className="accent-ember-500"
              />
              {status.replace("_", " ")}
            </label>
          ))}
          <button
            type="button"
            onClick={() => onChange(new Set())}
            className="mt-1 text-[11px] text-ember-400 hover:text-ember-300"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}

type TaskFieldPatch = Partial<{
  title: string;
  start_date: string | null;
  due_date: string | null;
  assignee_id: string | null;
  priority: TaskPriority;
}>;

// Info (activity/responsible/dates/status/priority/score) and Gantt (day
// bars) render into two independent grids side by side - see the
// `columnsCollapsed`/`infoCellStyle` split in SchedulePage below - so each
// gets its own horizontal scrollbar and the info columns can collapse
// without reshuffling the day grid's column math.
function ScheduleActivityInfoRow({
  row,
  rowIndex,
  members,
  projectId,
  isCollapsed,
  columnsCollapsed,
  isHighlighted,
  onToggleCollapse,
  onFieldChange,
  onStatusChange,
  onUnparent,
  onHoverChange,
  infoCellStyle,
}: {
  row: ScheduleRow;
  rowIndex: number;
  members: ProjectMemberDetailResponse[];
  projectId: string;
  isCollapsed: boolean;
  columnsCollapsed: boolean;
  isHighlighted: boolean;
  onToggleCollapse: (taskId: string) => void;
  onFieldChange: (taskId: string, patch: TaskFieldPatch) => void;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  onUnparent: (taskId: string) => void;
  onHoverChange: (taskId: string | null) => void;
  infoCellStyle: (colIndex: number, rowIndex: number) => CSSProperties;
}) {
  const { task } = row;
  const { attributes, listeners, setNodeRef: setDragRef, isDragging } = useDraggable({
    id: task.id,
  });
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: task.id });
  // A hovered activity's row (and its date range in the header - see
  // hoveredRange in SchedulePage) gets a lighter background so it's obvious
  // which row a highlighted date range belongs to.
  const rowBg = isHighlighted ? "bg-ink-800" : "bg-ink-900";

  function setCombinedRef(node: HTMLDivElement | null) {
    setDragRef(node);
    setDropRef(node);
  }

  return (
    <Fragment>
      <div
        ref={setCombinedRef}
        {...listeners}
        {...attributes}
        onClick={() => {
          if (row.hasChildren) onToggleCollapse(task.id);
        }}
        onMouseEnter={() => onHoverChange(task.id)}
        onMouseLeave={() => onHoverChange(null)}
        title={
          row.hasChildren
            ? "Click to expand/collapse - drag onto another activity to make it a subtask"
            : "Drag onto another activity to make it a subtask"
        }
        className={`flex cursor-grab items-center gap-1 border-b border-r border-ink-800 px-1 text-slate-500 active:cursor-grabbing ${
          isOver ? "bg-ember-500/20" : rowBg
        } ${isDragging ? "opacity-50" : ""}`}
        style={infoCellStyle(0, rowIndex)}
      >
        {row.hasChildren && (
          <span className="shrink-0 text-slate-400">{isCollapsed ? "▸" : "▾"}</span>
        )}
        <span className="truncate">{row.number}</span>
      </div>
      <div
        onMouseEnter={() => onHoverChange(task.id)}
        onMouseLeave={() => onHoverChange(null)}
        className={`flex items-center gap-1 truncate border-b border-r border-ink-800 px-1 text-slate-200 ${rowBg}`}
        style={{ ...infoCellStyle(1, rowIndex), paddingLeft: 4 + row.depth * 14 }}
      >
        <Link
          to={`/projects/${projectId}/tasks/${task.id}`}
          title={task.title}
          className="truncate text-slate-200 hover:text-ember-400 hover:underline"
        >
          {task.title}
        </Link>
        {task.parent_task_id && (
          <button
            onClick={() => onUnparent(task.id)}
            title="Remove from parent"
            className="shrink-0 text-slate-600 hover:text-red-400"
          >
            ×
          </button>
        )}
      </div>
      {!columnsCollapsed && (
        <>
          <select
            value={task.assignee_id ?? ""}
            onChange={(e) => onFieldChange(task.id, { assignee_id: e.target.value || null })}
            className={`h-full w-full truncate border-b border-r border-ink-800 px-1 text-slate-400 outline-none ${rowBg}`}
            style={infoCellStyle(2, rowIndex)}
          >
            <option value="">—</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.full_name}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={task.start_date ?? ""}
            onChange={(e) => onFieldChange(task.id, { start_date: e.target.value || null })}
            className={`h-full w-full border-b border-r border-ink-800 px-1 text-slate-400 outline-none ${rowBg}`}
            style={infoCellStyle(3, rowIndex)}
          />
          <input
            type="date"
            value={task.due_date ?? ""}
            onChange={(e) => onFieldChange(task.id, { due_date: e.target.value || null })}
            className={`h-full w-full border-b border-r border-ink-800 px-1 text-slate-400 outline-none ${rowBg}`}
            style={infoCellStyle(4, rowIndex)}
          />
          <select
            value={task.status}
            onChange={(e) => onStatusChange(task.id, e.target.value as TaskStatus)}
            className={`h-full w-full border-b border-r border-ink-800 px-1 text-[10px] uppercase text-slate-400 outline-none ${rowBg}`}
            style={infoCellStyle(5, rowIndex)}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status.replace("_", " ")}
              </option>
            ))}
          </select>
          <div
            className={`flex items-center border-b border-r border-ink-800 px-2 ${rowBg}`}
            style={infoCellStyle(6, rowIndex)}
          >
            <select
              value={task.priority}
              onChange={(e) =>
                onFieldChange(task.id, { priority: e.target.value as TaskPriority })
              }
              className={`cursor-pointer appearance-none rounded-full border-none px-2 py-0.5 text-xs font-medium outline-none ${PRIORITY_COLORS[task.priority]}`}
            >
              {PRIORITY_OPTIONS.map((priority) => (
                <option key={priority} value={priority} className="bg-ink-900 text-slate-200">
                  {priority}
                </option>
              ))}
            </select>
          </div>
          <div
            className={`flex items-center border-b border-r border-ink-800 px-2 ${rowBg}`}
            style={infoCellStyle(7, rowIndex)}
          >
            {task.priority_score !== null && <PriorityScoreChip score={task.priority_score} />}
          </div>
        </>
      )}
    </Fragment>
  );
}

function ScheduleActivityGanttRow({
  task,
  rowIndex,
  range,
  segments,
  dayIndex,
  isHighlighted,
  onHoverChange,
}: {
  task: TaskResponse;
  rowIndex: number;
  range: EffectiveRange;
  segments: BarSegment[];
  dayIndex: Map<string, number>;
  isHighlighted: boolean;
  onHoverChange: (taskId: string | null) => void;
}) {
  return (
    <Fragment>
      {segments.map((segment, segIndex) => {
        const startCol = (dayIndex.get(segment.startIso) ?? 0) + 1;
        const endCol = (dayIndex.get(segment.endIso) ?? dayIndex.get(segment.startIso) ?? 0) + 1;
        return (
          <div
            key={`bar-${task.id}-${segIndex}`}
            onMouseEnter={() => onHoverChange(task.id)}
            onMouseLeave={() => onHoverChange(null)}
            className={`flex items-center border-b border-ink-800 px-0.5 ${
              isHighlighted ? "bg-ink-800" : ""
            }`}
            style={{ gridRow: rowIndex, gridColumn: `${startCol} / ${endCol + 1}` }}
          >
            <div
              title={
                range.isRollup
                  ? `${task.title} — rollup of subtasks: ${range.start} → ${range.due}`
                  : `${task.title} — Planned: ${task.days_planned ?? "—"}d, Taken: ${task.days_taken ?? "—"}d`
              }
              className={`w-full rounded ${segment.color} ${range.isRollup ? "h-2" : "h-4"} ${
                isHighlighted ? "ring-2 ring-slate-100" : ""
              }`}
            />
          </div>
        );
      })}
    </Fragment>
  );
}

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [activityFilter, setActivityFilter] = useState("");
  const [responsibleFilter, setResponsibleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<Set<TaskStatus>>(new Set());
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");
  const [dueTodayFilter, setDueTodayFilter] = useState(false);
  const [sortKey, setSortKey] = useState<ScheduleSortKey>("entry");
  const [sortDirection, setSortDirection] = useState<ScheduleSortDirection>("asc");
  const [isExporting, setIsExporting] = useState(false);
  const [columnsCollapsed, setColumnsCollapsed] = useState(false);
  const [hoveredTaskId, setHoveredTaskId] = useState<string | null>(null);

  // The Gantt pane is the only one with a visible scrollbar (vertical *and*
  // horizontal) - the info pane's own vertical scroll is hidden
  // (overflow-hidden) and mirrors the Gantt's scrollTop programmatically, so
  // there's a single vertical scrollbar on screen instead of one per pane.
  // Wheel/trackpad scrolling while the pointer is over the info columns is
  // forwarded to the Gantt pane so it still feels scrollable there too.
  const infoPaneRef = useRef<HTMLDivElement>(null);
  const ganttPaneRef = useRef<HTMLDivElement>(null);

  function handleGanttScroll(event: UIEvent<HTMLDivElement>) {
    if (infoPaneRef.current) {
      infoPaneRef.current.scrollTop = event.currentTarget.scrollTop;
    }
  }

  function handleInfoPaneWheel(event: WheelEvent<HTMLDivElement>) {
    if (ganttPaneRef.current) {
      ganttPaneRef.current.scrollTop += event.deltaY;
    }
  }

  function toggleSort(key: ScheduleSortKey) {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  }
  const [pendingStatus, setPendingStatus] = useState<{ taskId: string; status: TaskStatus } | null>(
    null,
  );
  const [showNewTaskForm, setShowNewTaskForm] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskParentId, setNewTaskParentId] = useState("");
  const [newTaskAssigneeId, setNewTaskAssigneeId] = useState("");
  const [newTaskStart, setNewTaskStart] = useState("");
  const [newTaskDue, setNewTaskDue] = useState("");
  const [error, setError] = useState<string | null>(null);

  // A distance threshold so a plain click on the drag handle (used to
  // toggle collapse) isn't swallowed as a drag by sub-pixel pointer jitter.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, taskData, memberData] = await Promise.all([
        getProject(token, projectId),
        listProjectTasks(token, projectId, { include_subtasks: true }),
        listProjectMembers(token, projectId),
      ]);
      setProject(projectData);
      setTasks(taskData);
      setMembers(memberData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load schedule");
    }
  }

  function toggleCollapse(taskId: string) {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }

  async function handleFieldChange(taskId: string, patch: TaskFieldPatch) {
    if (!token) return;
    const task = tasks.find((i) => i.id === taskId);
    if (!task) return;
    const previous = tasks;
    setTasks((current) => current.map((i) => (i.id === taskId ? { ...i, ...patch } : i)));
    try {
      const updated = await updateTask(token, taskId, {
        title: patch.title ?? task.title,
        priority: patch.priority ?? task.priority,
        assignee_id: "assignee_id" in patch ? (patch.assignee_id ?? null) : task.assignee_id,
        start_date: "start_date" in patch ? (patch.start_date ?? null) : task.start_date,
        due_date: "due_date" in patch ? (patch.due_date ?? null) : task.due_date,
      });
      setTasks((current) => current.map((i) => (i.id === taskId ? updated : i)));
    } catch (err) {
      setTasks(previous);
      setError(err instanceof Error ? err.message : "Failed to update task");
    }
  }

  async function handleExport() {
    if (!token || !projectId) return;
    setIsExporting(true);
    try {
      await downloadProjectExport(token, projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export workbook");
    } finally {
      setIsExporting(false);
    }
  }

  async function applyStatusChange(taskId: string, status: TaskStatus) {
    if (!token) return;
    const previous = tasks;
    setTasks((current) => current.map((i) => (i.id === taskId ? { ...i, status } : i)));
    try {
      const updated = await updateTaskStatus(token, taskId, status);
      setTasks((current) => current.map((i) => (i.id === taskId ? updated : i)));
    } catch (err) {
      setTasks(previous);
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  function handleStatusChange(taskId: string, status: TaskStatus) {
    if (status === "done") {
      setPendingStatus({ taskId, status });
      return;
    }
    void applyStatusChange(taskId, status);
  }

  async function handleReparent(taskId: string, parentTaskId: string | null) {
    if (!token) return;
    const task = tasks.find((i) => i.id === taskId);
    if (!task) return;
    const previous = tasks;
    setTasks((current) =>
      current.map((i) => (i.id === taskId ? { ...i, parent_task_id: parentTaskId } : i)),
    );
    try {
      const updated = await updateTaskParent(token, taskId, parentTaskId);
      setTasks((current) => current.map((i) => (i.id === taskId ? updated : i)));
    } catch (err) {
      setTasks(previous);
      setError(err instanceof Error ? err.message : "Failed to reparent task");
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const taskId = String(active.id);
    const parentTaskId = String(over.id);
    if (taskId === parentTaskId) return;
    const task = tasks.find((item) => item.id === taskId);
    const parent = tasks.find((item) => item.id === parentTaskId);
    if (!task || !parent) return;
    if (parent.parent_task_id !== null) {
      setError("A Subtask cannot be used as a parent.");
      return;
    }
    if (task.parent_task_id === parentTaskId) return;
    if (task.parent_task_id === null && tasks.some((child) => child.parent_task_id === task.id)) {
      setError("Move or promote this Task's Subtasks before assigning it to another Task.");
      return;
    }
    void handleReparent(taskId, parentTaskId);
  }

  async function handleCreateTask() {
    if (!token || !projectId || !newTaskTitle.trim()) return;
    try {
      const fields = {
        title: newTaskTitle.trim(),
        assignee_id: newTaskAssigneeId || null,
        start_date: newTaskStart || null,
        due_date: newTaskDue || null,
      };
      const created = newTaskParentId
        ? await createSubtask(token, newTaskParentId, fields)
        : await createTask(token, projectId, fields);
      setTasks((current) => [...current, created]);
      setNewTaskTitle("");
      setNewTaskParentId("");
      setNewTaskAssigneeId("");
      setNewTaskStart("");
      setNewTaskDue("");
      setShowNewTaskForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create activity");
    }
  }

  const effectiveRanges = useMemo(() => buildEffectiveRanges(tasks), [tasks]);

  const datedTasks = useMemo(
    () => tasks.filter((task) => effectiveRanges.get(task.id)?.due != null),
    [tasks, effectiveRanges],
  );

  const todayIso = isoDate(new Date());

  const filters: ScheduleFilters = {
    activity: activityFilter,
    responsible: responsibleFilter,
    status: statusFilter,
    priority: priorityFilter,
    dueToday: dueTodayFilter,
  };
  const hasActiveFilter =
    filters.activity.trim() !== "" ||
    filters.responsible !== "" ||
    filters.status.size > 0 ||
    filters.priority !== "" ||
    filters.dueToday;

  const scheduleRows = useMemo(() => {
    // Filtering ignores collapse state entirely (a match hidden under a
    // collapsed ancestor would be invisible with no way to reveal it), and
    // restores the normal collapsed view once every filter is cleared.
    const rows = buildScheduleRows(
      tasks,
      hasActiveFilter ? new Set() : collapsed,
      sortKey,
      sortDirection,
    );
    if (!hasActiveFilter) return rows;
    const keep = computeFilterKeepSet(tasks, filters, todayIso);
    return rows.filter((row) => keep.has(row.task.id));
  }, [
    tasks,
    collapsed,
    hasActiveFilter,
    todayIso,
    sortKey,
    sortDirection,
    filters.activity,
    filters.responsible,
    filters.status,
    filters.priority,
    filters.dueToday,
  ]);

  const { days, weeks, months } = useMemo(() => {
    const today = new Date();
    const dates: Date[] = [today];
    for (const task of datedTasks) {
      const range = effectiveRanges.get(task.id);
      if (range?.start) dates.push(parseLocalDate(range.start));
      if (range?.due) dates.push(parseLocalDate(range.due));
      if (task.closed_at_date) dates.push(parseLocalDate(task.closed_at_date));
    }

    const minDate = startOfWeek(new Date(Math.min(...dates.map((d) => d.getTime()))));
    const maxDate = endOfWeek(new Date(Math.max(...dates.map((d) => d.getTime()))));

    const dayList: Date[] = [];
    for (let d = minDate; d <= maxDate; d = addDays(d, 1)) {
      dayList.push(d);
    }

    const weekGroups: { label: string; span: number }[] = [];
    for (const day of dayList) {
      const label = `W${weekNumber(day)}`;
      const last = weekGroups[weekGroups.length - 1];
      if (last && last.label === label) {
        last.span += 1;
      } else {
        weekGroups.push({ label, span: 1 });
      }
    }

    const monthGroups: { label: string; span: number }[] = [];
    for (const day of dayList) {
      const label = day.toLocaleDateString("en-US", { month: "long", year: "numeric" });
      const last = monthGroups[monthGroups.length - 1];
      if (last && last.label === label) {
        last.span += 1;
      } else {
        monthGroups.push({ label, span: 1 });
      }
    }

    return { days: dayList, weeks: weekGroups, months: monthGroups };
  }, [datedTasks, effectiveRanges]);

  const dayIndex = useMemo(() => {
    const map = new Map<string, number>();
    days.forEach((d, i) => map.set(isoDate(d), i));
    return map;
  }, [days]);

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  const visibleStickyColumns = columnsCollapsed
    ? STICKY_COLUMNS.filter((col) => !COLLAPSIBLE_COLUMN_KEYS.has(col.key))
    : STICKY_COLUMNS;
  const infoGridTemplateColumns = visibleStickyColumns.map((col) => `${col.width}px`).join(" ");
  const ganttGridTemplateColumns = days.map(() => `${DAY_WIDTH}px`).join(" ");
  const pendingTask = pendingStatus ? tasks.find((i) => i.id === pendingStatus.taskId) : null;

  // The activity currently hovered (from either its info row or its Gantt
  // bar - see onHoverChange below) - drives the header/row highlight the
  // user asked for. `range` reuses the same rollup-aware start/due
  // SchedulePage already computes for the bar itself, so a parent's
  // highlighted span matches its rolled-up bar exactly.
  const hoveredRange = hoveredTaskId ? effectiveRanges.get(hoveredTaskId) : null;

  // Horizontal position never needs `position: sticky` - the info columns
  // and the Gantt live in two separate grids side by side, each with its
  // own horizontal scroll, so a column simply never overlaps the other
  // pane in the first place. Vertical position does, for header cells only
  // (see infoHeaderCellStyle) - each pane scrolls its own rows underneath
  // its own fixed header.
  function infoCellStyle(colIndex: number, rowIndex: number): CSSProperties {
    return { gridRow: rowIndex, gridColumn: colIndex + 1 };
  }

  function infoHeaderCellStyle(colIndex: number, rowIndex: number): CSSProperties {
    return {
      gridRow: rowIndex,
      gridColumn: colIndex + 1,
      position: "sticky",
      top: (rowIndex - 1) * ROW_HEIGHT,
      zIndex: 10,
    };
  }

  return (
    <AppShell breadcrumb={project.name}>
      {/* `calc(100vh - 60px)`, not `h-full`/`h-screen`: AppShell's root only
          sets `min-h-screen` (a floor, not a cap), so nothing above this
          point in the tree has a definite height for `h-full`/percentage
          sizing to resolve against - `main` just grows to fit content
          instead of clipping it. A `vh` unit is viewport-relative and
          bypasses that broken chain entirely, which is what actually lets
          the Gantt pane's overflow-auto engage and cap it, instead of the
          whole page growing and pushing its scrollbar far below the fold
          again. The 60px subtracted is TopBar's rendered height (measured:
          border-box height 59px) - TopBar sits above this div too, so
          without subtracting it the page would need to scroll vertically by
          that amount to reveal the bottom of the Gantt pane. */}
      <div className="flex h-[calc(100vh-60px)] min-h-0 flex-col">
        <ProjectTabs projectId={project.id} />

        <div className="flex min-h-0 flex-1 flex-col p-4">
        {error && <p className="mb-3 shrink-0 text-sm text-red-400">{error}</p>}

        <div className="mb-3 flex shrink-0 items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDueTodayFilter((prev) => !prev)}
              title="Not done, and not scheduled to start in the future - includes overdue activities"
              className={`rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors ${
                dueTodayFilter
                  ? "border-ember-500 bg-ember-500/10 text-ember-400"
                  : "border-ink-700 bg-ink-850 text-slate-300 hover:border-ink-600"
              }`}
            >
              Due today
            </button>
            <button
              onClick={() => void handleExport()}
              disabled={isExporting}
              title="Download an Excel workbook with the Kanban board and this Timeline"
              className="flex items-center gap-1 rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:border-ink-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <DownloadIcon className="h-3.5 w-3.5" />
              {isExporting ? "Exporting…" : "Export to Excel"}
            </button>
            <button
              onClick={() => setColumnsCollapsed((prev) => !prev)}
              title={
                columnsCollapsed
                  ? "Show Responsible/Start/Due/Status/Priority/Score columns"
                  : "Hide every column except # and Activity, to give the Gantt more room"
              }
              className={`rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors ${
                columnsCollapsed
                  ? "border-ember-500 bg-ember-500/10 text-ember-400"
                  : "border-ink-700 bg-ink-850 text-slate-300 hover:border-ink-600"
              }`}
            >
              {columnsCollapsed ? "Expand columns" : "Collapse columns"}
            </button>
          </div>

          {showNewTaskForm ? (
            <div className="flex flex-wrap items-center justify-end gap-2">
              <input
                autoFocus
                type="text"
                placeholder="Activity title"
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateTask()}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <select
                value={newTaskParentId}
                onChange={(e) => setNewTaskParentId(e.target.value)}
                aria-label="Parent task"
                className="max-w-56 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              >
                <option value="">Top-level task</option>
                {tasks.filter((task) => task.parent_task_id === null).map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.title}
                  </option>
                ))}
              </select>
              <select
                value={newTaskAssigneeId}
                onChange={(e) => setNewTaskAssigneeId(e.target.value)}
                aria-label="Responsible person"
                className="max-w-56 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              >
                <option value="">Unassigned</option>
                {members.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {member.full_name}
                  </option>
                ))}
              </select>
              <input
                type="date"
                value={newTaskStart}
                onChange={(e) => setNewTaskStart(e.target.value)}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              />
              <input
                type="date"
                value={newTaskDue}
                onChange={(e) => setNewTaskDue(e.target.value)}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateTask}
                className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Create
              </button>
              <button
                onClick={() => setShowNewTaskForm(false)}
                className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowNewTaskForm(true)}
              className="flex items-center gap-1 rounded-md border border-dashed border-ink-700 px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:border-ink-600 hover:text-slate-300"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              New activity
            </button>
          )}
        </div>

        {scheduleRows.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            {hasActiveFilter ? (
              <>
                <p>No activities match these filters.</p>
                <button
                  onClick={() => {
                    setActivityFilter("");
                    setResponsibleFilter("");
                    setStatusFilter(new Set());
                    setPriorityFilter("");
                    setDueTodayFilter(false);
                  }}
                  className="mt-2 text-ember-400 hover:text-ember-300"
                >
                  Clear filters
                </button>
              </>
            ) : (
              <p>No activities yet — create one to get started.</p>
            )}
          </div>
        ) : (
          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            {/* Two independent grids side by side, each with its own
                horizontal scroll: the info columns never need to scroll
                (fixed width), and the Gantt gets a dedicated scrollbar of
                its own instead of sharing one with the columns. Both fill
                the remaining page height (see the h-full/flex-1 chain up to
                AppShell's <main>) and scroll vertically together - the
                Gantt pane is the only one with a visible scrollbar (see
                handleGanttScroll/handleInfoPaneWheel above), so there's one
                vertical scrollbar, on the right, instead of one per pane.
                Each header row is `position: sticky` within its own pane so
                column titles / week-day labels stay visible while scrolling
                down through a long schedule. */}
            <div className="flex min-h-0 flex-1 overflow-hidden rounded-md border border-ink-800">
              <div
                ref={infoPaneRef}
                className="min-h-0 shrink-0 overflow-y-hidden"
                onWheel={handleInfoPaneWheel}
              >
                <div
                  className="grid text-xs"
                  style={{ gridTemplateColumns: infoGridTemplateColumns, gridAutoRows: `${ROW_HEIGHT}px` }}
                >
                  {/* Header row 1: spacer (month band only applies to the Gantt side) */}
                  {visibleStickyColumns.map((col, i) => (
                    <div
                      key={`m-${col.key}`}
                      className="border-b border-r border-ink-800 bg-ink-900"
                      style={infoHeaderCellStyle(i, 1)}
                    />
                  ))}

                  {/* Header row 2: spacer (week band only applies to the Gantt side) */}
                  {visibleStickyColumns.map((col, i) => (
                    <div
                      key={`w-${col.key}`}
                      className="border-b border-r border-ink-800 bg-ink-900"
                      style={infoHeaderCellStyle(i, 2)}
                    />
                  ))}

                  {/* Header row 3: column titles */}
                  {visibleStickyColumns.map((col, i) => {
                    const columnSortKey: ScheduleSortKey | null =
                      col.key === "index"
                        ? "entry"
                        : col.key === "priority"
                          ? "priority"
                          : col.key === "score"
                            ? "score"
                            : null;
                    return (
                      <div
                        key={`h-${col.key}`}
                        className="border-b border-r border-ink-800 bg-ink-900 font-semibold text-slate-300"
                        style={infoHeaderCellStyle(i, 3)}
                      >
                        {columnSortKey ? (
                          <button
                            onClick={() => toggleSort(columnSortKey)}
                            title={`Sort by ${col.label.toLowerCase()}`}
                            className="flex h-full w-full items-center gap-1 px-2 hover:text-ember-400"
                          >
                            {col.label}
                            {sortKey === columnSortKey && (
                              <span className="text-ember-400">
                                {sortDirection === "asc" ? "▲" : "▼"}
                              </span>
                            )}
                          </button>
                        ) : (
                          <div className="flex h-full items-center px-2">{col.label}</div>
                        )}
                      </div>
                    );
                  })}

                  {/* Header row 4: per-column filters */}
                  {visibleStickyColumns.map((col, i) => (
                    <div
                      key={`filter-${col.key}`}
                      className="flex items-center border-b border-r border-ink-800 bg-ink-900 px-1"
                      style={infoHeaderCellStyle(i, 4)}
                    >
                      {col.key === "activity" && (
                        <input
                          type="text"
                          placeholder="Filter..."
                          value={activityFilter}
                          onChange={(e) => setActivityFilter(e.target.value)}
                          className="w-full rounded border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-[11px] text-slate-200 outline-none focus:border-ember-500"
                        />
                      )}
                      {col.key === "responsible" && (
                        <select
                          value={responsibleFilter}
                          onChange={(e) => setResponsibleFilter(e.target.value)}
                          className="w-full rounded border border-ink-700 bg-ink-800 px-1 py-0.5 text-[11px] text-slate-300 outline-none focus:border-ember-500"
                        >
                          <option value="">All</option>
                          <option value={UNASSIGNED_FILTER_VALUE}>Unassigned</option>
                          {members.map((member) => (
                            <option key={member.user_id} value={member.user_id}>
                              {member.full_name}
                            </option>
                          ))}
                        </select>
                      )}
                      {col.key === "status" && (
                        <StatusFilterDropdown selected={statusFilter} onChange={setStatusFilter} />
                      )}
                      {col.key === "priority" && (
                        <select
                          value={priorityFilter}
                          onChange={(e) => setPriorityFilter(e.target.value as TaskPriority | "")}
                          className="w-full rounded border border-ink-700 bg-ink-800 px-1 py-0.5 text-[11px] text-slate-300 outline-none focus:border-ember-500"
                        >
                          <option value="">All</option>
                          {PRIORITY_OPTIONS.map((priority) => (
                            <option key={priority} value={priority}>
                              {priority}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  ))}

                  {/* Task rows */}
                  {scheduleRows.map((row, rowOffset) => (
                    <ScheduleActivityInfoRow
                      key={row.task.id}
                      row={row}
                      rowIndex={HEADER_ROWS + 1 + rowOffset}
                      members={members}
                      projectId={project.id}
                      isCollapsed={collapsed.has(row.task.id)}
                      columnsCollapsed={columnsCollapsed}
                      isHighlighted={hoveredTaskId === row.task.id}
                      onToggleCollapse={toggleCollapse}
                      onFieldChange={handleFieldChange}
                      onStatusChange={handleStatusChange}
                      onUnparent={(taskId) => void handleReparent(taskId, null)}
                      onHoverChange={setHoveredTaskId}
                      infoCellStyle={infoCellStyle}
                    />
                  ))}
                </div>
              </div>

              <div
                ref={ganttPaneRef}
                onScroll={handleGanttScroll}
                className="min-h-0 min-w-0 flex-1 overflow-auto"
              >
                <div
                  className="grid text-xs"
                  style={{ gridTemplateColumns: ganttGridTemplateColumns, gridAutoRows: `${ROW_HEIGHT}px` }}
                >
                  {/* Header row 1: month band */}
                  {months.map((month, i) => {
                    const startCol = 1 + months.slice(0, i).reduce((s, m) => s + m.span, 0);
                    return (
                      <div
                        key={`month-${month.label}-${i}`}
                        className="flex items-center justify-center border-b border-r border-ink-800 bg-ink-900 font-semibold text-slate-300"
                        style={{
                          gridRow: 1,
                          gridColumn: `${startCol} / ${startCol + month.span}`,
                          position: "sticky",
                          top: 0,
                          zIndex: 10,
                        }}
                      >
                        {month.label}
                      </div>
                    );
                  })}

                  {/* Header row 2: week band */}
                  {weeks.map((week, i) => {
                    const startCol = 1 + weeks.slice(0, i).reduce((s, w) => s + w.span, 0);
                    return (
                      <div
                        key={`week-${week.label}-${i}`}
                        className="flex items-center justify-center border-b border-r border-ink-800 bg-ink-900 font-semibold text-slate-300"
                        style={{
                          gridRow: 2,
                          gridColumn: `${startCol} / ${startCol + week.span}`,
                          position: "sticky",
                          top: ROW_HEIGHT,
                          zIndex: 10,
                        }}
                      >
                        {week.label}
                      </div>
                    );
                  })}

                  {/* Header row 3: day letter/date */}
                  {days.map((day, i) => {
                    const iso = isoDate(day);
                    const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                    const isToday = iso === todayIso;
                    const isHighlighted =
                      !!hoveredRange?.start &&
                      !!hoveredRange.due &&
                      iso >= hoveredRange.start &&
                      iso <= hoveredRange.due;
                    return (
                      <div
                        key={`day-${iso}`}
                        className={`flex flex-col items-center justify-center border-b border-r border-ink-800 text-[10px] ${
                          isToday
                            ? "bg-ember-500/30 text-slate-100"
                            : isHighlighted
                              ? "bg-sky-500/30 text-slate-100"
                              : isWeekend
                                ? "bg-ink-850 text-slate-500"
                                : "bg-ink-900 text-slate-400"
                        }`}
                        style={{
                          gridRow: 3,
                          gridColumn: i + 1,
                          position: "sticky",
                          top: ROW_HEIGHT * 2,
                          zIndex: 10,
                        }}
                      >
                        <span>{DAY_LETTERS[day.getDay()]}</span>
                        <span>{day.getDate()}</span>
                      </div>
                    );
                  })}

                  {/* Header row 4: spacer */}
                  <div
                    className="border-b border-ink-800 bg-ink-900"
                    style={{
                      gridRow: 4,
                      gridColumn: "1 / -1",
                      position: "sticky",
                      top: ROW_HEIGHT * 3,
                      zIndex: 10,
                    }}
                  />

                  {/* Task bars */}
                  {scheduleRows.map((row, rowOffset) => {
                    const range = effectiveRanges.get(row.task.id)!;
                    const segments: BarSegment[] = range.isRollup
                      ? range.start && range.due
                        ? [{ startIso: range.start, endIso: range.due, color: "bg-indigo-400" }]
                        : []
                      : computeBarSegments(row.task, todayIso);

                    return (
                      <ScheduleActivityGanttRow
                        key={row.task.id}
                        task={row.task}
                        rowIndex={HEADER_ROWS + 1 + rowOffset}
                        range={range}
                        segments={segments}
                        dayIndex={dayIndex}
                        isHighlighted={hoveredTaskId === row.task.id}
                        onHoverChange={setHoveredTaskId}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          </DndContext>
        )}
        </div>
      </div>

      {pendingStatus && (
        <Modal title="Close this activity?" onClose={() => setPendingStatus(null)}>
          <p className="text-sm text-slate-400">
            Marking <span className="text-slate-200">{pendingTask?.title ?? "this activity"}</span>{" "}
            as done will record the close date. This can be reopened later by changing its status
            again.
          </p>
          <ModalActions>
            <button
              onClick={() => setPendingStatus(null)}
              className="rounded-md border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                void applyStatusChange(pendingStatus.taskId, pendingStatus.status);
                setPendingStatus(null);
              }}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Close activity
            </button>
          </ModalActions>
        </Modal>
      )}
    </AppShell>
  );
}
