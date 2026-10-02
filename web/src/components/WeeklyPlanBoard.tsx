import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { ProjectResponse } from "../api/client";
import type { TaskResponse, TaskStatus } from "../api/client_tasks";
import { STATUS_LABELS } from "./TaskBadges";

const DAY_COUNT = 7;
const STATUSES = Object.keys(STATUS_LABELS) as TaskStatus[];

export function startOfWeek(value: Date): Date {
  const result = new Date(value);
  result.setHours(0, 0, 0, 0);
  const daysSinceMonday = (result.getDay() + 6) % DAY_COUNT;
  result.setDate(result.getDate() - daysSinceMonday);
  return result;
}

export function addDays(value: Date, amount: number): Date {
  const result = new Date(value);
  result.setDate(result.getDate() + amount);
  return result;
}

export function localDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function resolveTaskDueDateMove(
  activeId: string,
  overId: string | undefined,
  tasks: TaskResponse[],
): { taskId: string; dueDate: string } | null {
  if (!overId?.startsWith("day:")) return null;
  const dueDate = overId.slice(4);
  const task = tasks.find((candidate) => candidate.id === activeId);
  if (!task || task.due_date === dueDate) return null;
  return { taskId: task.id, dueDate };
}

function WeeklyTaskCard({
  task,
  project,
  onChangeStatus,
}: {
  task: TaskResponse;
  project: ProjectResponse | undefined;
  onChangeStatus: (taskId: string, status: TaskStatus) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <article
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`cursor-grab rounded-md border bg-ink-800 p-2.5 shadow-sm active:cursor-grabbing ${
        task.status === "done" ? "border-emerald-900/70" : "border-ink-700"
      } ${isDragging ? "z-20 opacity-70 shadow-xl shadow-black/30" : ""}`}
    >
      <Link
        to={`/projects/${task.project_id}/tasks/${task.id}`}
        onClick={(event) => isDragging && event.preventDefault()}
        className={`block text-sm font-medium leading-5 transition-colors hover:text-ember-400 ${
          task.status === "done" ? "text-slate-400 line-through" : "text-slate-100"
        }`}
      >
        {task.title}
      </Link>
      <p className="mt-1 truncate text-[11px] text-slate-500" title={project?.name}>
        {project?.name ?? "Unknown project"}
      </p>
      <div className="mt-2 flex items-center justify-between gap-1">
        <select
          aria-label={`Status for ${task.title}`}
          value={task.status}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}
          onChange={(event) => onChangeStatus(task.id, event.target.value as TaskStatus)}
          className={`max-w-full cursor-pointer rounded-full border border-transparent px-1.5 py-0.5 text-[11px] font-medium outline-none ${
            task.status === "done"
              ? "bg-emerald-500/15 text-emerald-300"
              : task.status === "in_progress"
                ? "bg-amber-500/15 text-amber-300"
                : "bg-slate-950/40 text-slate-300"
          }`}
        >
          {STATUSES.map((status) => (
            <option key={status} value={status}>{STATUS_LABELS[status]}</option>
          ))}
        </select>
        {task.status === "done" && (
          <span className="text-xs font-medium text-emerald-400" aria-label="Completed">
            ✓
          </span>
        )}
      </div>
    </article>
  );
}

function WeekdayColumn({
  date,
  tasks,
  hiddenTaskIds,
  projectsById,
  isToday,
  onCreateTask,
  onChangeStatus,
  onChangeVisibility,
}: {
  date: Date;
  tasks: TaskResponse[];
  hiddenTaskIds: string[];
  projectsById: Map<string, ProjectResponse>;
  isToday: boolean;
  onCreateTask: (dueDate: string) => void;
  onChangeStatus: (taskId: string, status: TaskStatus) => void;
  onChangeVisibility: (taskIds: string[], visible: boolean) => void;
}) {
  const dateKey = localDateKey(date);
  const { setNodeRef, isOver } = useDroppable({ id: `day:${dateKey}` });
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const visibleTasks = tasks.filter((task) => !hiddenTaskIds.includes(task.id));
  const allVisible = visibleTasks.length === tasks.length;

  return (
    <section
      ref={setNodeRef}
      aria-label={date.toLocaleDateString(undefined, { weekday: "long" })}
      className={`flex min-h-72 flex-col border-r border-ink-800 p-2 last:border-r-0 ${
        isOver ? "bg-ember-500/20" : isToday ? "bg-sky-500/5" : "bg-ink-900"
      }`}
    >
      <header className="relative mb-2 border-b border-ink-800 pb-2 text-center">
        <button
          type="button"
          aria-label={`Create task for ${dateKey}`}
          title="Create Task for this day"
          onClick={() => onCreateTask(dateKey)}
          className="absolute right-0 top-0 flex h-6 w-6 items-center justify-center rounded text-base text-slate-500 hover:bg-ink-800 hover:text-ember-400"
        >
          +
        </button>
        <p className={`text-xs font-semibold uppercase tracking-wide ${isToday ? "text-sky-400" : "text-slate-400"}`}>
          {date.toLocaleDateString(undefined, { weekday: "short" })}
        </p>
        <p className={`mx-auto mt-1 flex h-7 w-7 items-center justify-center rounded-full text-sm ${
          isToday ? "bg-sky-500 font-semibold text-white" : "text-slate-300"
        }`}>
          {date.getDate()}
        </p>
        {tasks.length > 0 && (
          <div className="relative mt-2 text-left">
            <button
              type="button"
              aria-label={`Filter ${dateKey} tasks`}
              onClick={() => setIsFilterOpen((current) => !current)}
              className={`flex w-full items-center justify-between rounded border px-2 py-1 text-[11px] ${
                allVisible
                  ? "border-ink-700 text-slate-400"
                  : "border-ember-500/60 bg-ember-500/10 text-ember-300"
              }`}
            >
              <span>Filter</span>
              <span> ▾</span>
            </button>
            {isFilterOpen && (
              <div className="absolute left-0 top-full z-30 mt-1 w-56 rounded-md border border-ink-700 bg-ink-850 p-2 shadow-xl shadow-black/40">
                <label className="flex cursor-pointer items-center gap-2 border-b border-ink-700 px-1 pb-2 text-xs font-medium text-slate-200">
                  <input
                    type="checkbox"
                    aria-label={`Show all tasks for ${dateKey}`}
                    checked={allVisible}
                    onChange={(event) => onChangeVisibility(
                      tasks.map((task) => task.id),
                      event.target.checked,
                    )}
                  />
                  Select all
                </label>
                <div className="max-h-48 space-y-1 overflow-y-auto py-2">
                  {tasks.map((task) => {
                    const checked = !hiddenTaskIds.includes(task.id);
                    return (
                      <label key={task.id} className="flex cursor-pointer items-start gap-2 rounded px-1 py-1 text-xs text-slate-300 hover:bg-ink-800">
                        <input
                          type="checkbox"
                          aria-label={`Show ${task.title}`}
                          checked={checked}
                          onChange={(event) =>
                            onChangeVisibility([task.id], event.target.checked)
                          }
                        />
                        <span className="line-clamp-2">{task.title}</span>
                      </label>
                    );
                  })}
                </div>
                <button
                  type="button"
                  onClick={() => setIsFilterOpen(false)}
                  className="w-full rounded bg-ink-700 px-2 py-1 text-xs text-slate-200 hover:bg-ink-600"
                >
                  Done
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      <div className="flex-1 space-y-2">
        {visibleTasks.map((task) => (
          <WeeklyTaskCard
            key={task.id}
            task={task}
            project={projectsById.get(task.project_id)}
            onChangeStatus={onChangeStatus}
          />
        ))}
        {tasks.length === 0 && (
          <div className="flex min-h-20 items-center justify-center rounded-md border border-dashed border-ink-800 px-2 text-center text-xs text-slate-600">
            Drop a task here
          </div>
        )}
        {tasks.length > 0 && visibleTasks.length === 0 && (
          <div className="flex min-h-20 items-center justify-center rounded-md border border-dashed border-ink-700 px-2 text-center text-xs text-slate-500">
            No Tasks selected
          </div>
        )}
      </div>
    </section>
  );
}

export default function WeeklyPlanBoard({
  tasks,
  projects,
  onMoveTask,
  onCreateTask,
  onChangeStatus,
}: {
  tasks: TaskResponse[];
  projects: ProjectResponse[];
  onMoveTask: (taskId: string, dueDate: string) => void;
  onCreateTask: (dueDate: string) => void;
  onChangeStatus: (taskId: string, status: TaskStatus) => void;
}) {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [hiddenTaskIds, setHiddenTaskIds] = useState<string[]>([]);
  const todayKey = localDateKey(new Date());
  const currentWeekKey = localDateKey(startOfWeek(new Date()));
  const days = useMemo(
    () => Array.from({ length: DAY_COUNT }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );
  const projectsById = useMemo(
    () => new Map(projects.map((project) => [project.id, project])),
    [projects],
  );
  const weekDateKeys = useMemo(
    () => new Set(days.map(localDateKey)),
    [days],
  );
  const visibleWeekTasks = useMemo(
    () => tasks.filter(
      (task) => task.due_date
        && weekDateKeys.has(task.due_date)
        && !hiddenTaskIds.includes(task.id),
    ),
    [hiddenTaskIds, tasks, weekDateKeys],
  );
  const completedVisibleTasks = visibleWeekTasks.filter((task) => task.status === "done").length;
  const weeklyProgress = visibleWeekTasks.length === 0
    ? 0
    : Math.round((completedVisibleTasks / visibleWeekTasks.length) * 100);
  const weekEnd = days[DAY_COUNT - 1];

  function handleVisibilityChange(taskIds: string[], visible: boolean) {
    const changedIds = new Set(taskIds);
    setHiddenTaskIds((current) => visible
      ? current.filter((id) => !changedIds.has(id))
      : [...new Set([...current, ...taskIds])]);
  }

  function handleDragEnd(event: DragEndEvent) {
    const move = resolveTaskDueDateMove(
      String(event.active.id),
      event.over ? String(event.over.id) : undefined,
      tasks,
    );
    if (move) onMoveTask(move.taskId, move.dueDate);
  }

  return (
    <section className="rounded-lg border border-ink-800 bg-ink-900 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="font-semibold text-slate-100">Weekly plan</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {localDateKey(weekStart) === currentWeekKey ? "Current week · " : ""}
              {weekStart.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              {" – "}
              {weekEnd.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
            </p>
          </div>
          <div
            role="progressbar"
            aria-label="Weekly progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={weeklyProgress}
            className="relative h-12 w-12 shrink-0"
          >
            <svg className="h-full w-full -rotate-90" viewBox="0 0 48 48" aria-hidden="true">
              <circle
                cx="24"
                cy="24"
                r="19"
                fill="none"
                stroke="currentColor"
                strokeWidth="5"
                className="text-ink-700"
              />
              <circle
                cx="24"
                cy="24"
                r="19"
                fill="none"
                pathLength="100"
                stroke="currentColor"
                strokeWidth="5"
                strokeLinecap="round"
                strokeDasharray={`${weeklyProgress} 100`}
                className="text-emerald-500 transition-[stroke-dasharray] duration-500"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-slate-100">
              {weeklyProgress}%
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Previous week"
            onClick={() => setWeekStart((current) => addDays(current, -DAY_COUNT))}
            className="rounded-md border border-ink-700 px-2.5 py-1.5 text-sm text-slate-300 hover:border-ink-600 hover:bg-ink-800"
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => setWeekStart(startOfWeek(new Date()))}
            className="rounded-md border border-ink-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-ink-600 hover:bg-ink-800"
          >
            Today
          </button>
          <button
            type="button"
            aria-label="Next week"
            onClick={() => setWeekStart((current) => addDays(current, DAY_COUNT))}
            className="rounded-md border border-ink-700 px-2.5 py-1.5 text-sm text-slate-300 hover:border-ink-600 hover:bg-ink-800"
          >
            →
          </button>
        </div>
      </div>

      <DndContext onDragEnd={handleDragEnd}>
        <div className="overflow-x-auto">
          <div className="grid min-w-[70rem] grid-cols-7">
            {days.map((date) => {
              const dateKey = localDateKey(date);
              const dayTasks = tasks
                .filter((task) => task.due_date === dateKey)
                .sort((a, b) => {
                  if (a.status === "done" && b.status !== "done") return 1;
                  if (a.status !== "done" && b.status === "done") return -1;
                  return a.title.localeCompare(b.title);
                });
              return (
                <WeekdayColumn
                  key={dateKey}
                  date={date}
                  tasks={dayTasks}
                  hiddenTaskIds={hiddenTaskIds}
                  projectsById={projectsById}
                  isToday={dateKey === todayKey}
                  onCreateTask={onCreateTask}
                  onChangeStatus={onChangeStatus}
                  onChangeVisibility={handleVisibilityChange}
                />
              );
            })}
          </div>
        </div>
      </DndContext>
    </section>
  );
}
