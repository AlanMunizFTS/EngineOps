import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { ProjectResponse } from "../api/client";
import type { IssueResponse, IssueStatus } from "../api/client_issues";
import { PriorityBadge, PriorityScoreChip, STATUS_LABELS } from "./IssueBadges";
import Modal, { ModalActions } from "./Modal";

const COLUMNS: Array<{ status: IssueStatus; accent: string }> = [
  { status: "backlog", accent: "bg-slate-400" },
  { status: "todo", accent: "bg-sky-400" },
  { status: "in_progress", accent: "bg-amber-400" },
  { status: "in_review", accent: "bg-violet-400" },
  { status: "done", accent: "bg-emerald-400" },
];

function compareCards(a: IssueResponse, b: IssueResponse): number {
  if (a.priority_score === null && b.priority_score === null) return 0;
  if (a.priority_score === null) return 1;
  if (b.priority_score === null) return -1;
  if (a.priority_score !== b.priority_score) return b.priority_score - a.priority_score;
  if (a.due_date === null && b.due_date === null) return 0;
  if (a.due_date === null) return 1;
  if (b.due_date === null) return -1;
  return a.due_date.localeCompare(b.due_date);
}

function formatDueDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function PersonalKanbanCard({
  issue,
  project,
}: {
  issue: IssueResponse;
  project: ProjectResponse | undefined;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: issue.id,
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
      className={`cursor-grab rounded-lg border border-ink-700 bg-ink-800 p-3 shadow-sm active:cursor-grabbing ${
        isDragging ? "z-10 opacity-70 shadow-xl shadow-black/30" : ""
      }`}
    >
      <Link
        to={`/projects/${issue.project_id}/issues/${issue.id}`}
        onClick={(event) => isDragging && event.preventDefault()}
        className="block text-sm font-medium leading-5 text-slate-100 transition-colors hover:text-ember-400"
      >
        {issue.title}
      </Link>

      <Link
        to={`/projects/${issue.project_id}`}
        onPointerDown={(event) => event.stopPropagation()}
        className="mt-1.5 block truncate text-xs text-slate-500 transition-colors hover:text-slate-300"
        title={project?.name ?? "Unknown project"}
      >
        {project?.name ?? "Unknown project"}
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <PriorityBadge priority={issue.priority} />
        <span className="rounded-full bg-ink-700 px-2 py-0.5 text-xs text-slate-400">
          {issue.issue_type}
        </span>
        {issue.priority_score !== null && <PriorityScoreChip score={issue.priority_score} />}
      </div>

      {(issue.due_date || issue.labels.length > 0) && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-ink-700 pt-2">
          {issue.due_date && (
            <span
              className={`text-xs ${issue.schedule_status === "late" ? "text-red-400" : "text-slate-500"}`}
            >
              Due {formatDueDate(issue.due_date)}
            </span>
          )}
          {issue.labels.slice(0, 2).map((label) => (
            <span
              key={label.id}
              className="max-w-24 truncate rounded-full border px-1.5 py-0.5 text-[10px] font-medium"
              style={{ borderColor: label.color, color: label.color }}
              title={label.name}
            >
              {label.name}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

function PersonalKanbanColumn({
  status,
  accent,
  issues,
  projectsById,
}: {
  status: IssueStatus;
  accent: string;
  issues: IssueResponse[];
  projectsById: Map<string, ProjectResponse>;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <section
      ref={setNodeRef}
      className={`flex min-h-[22rem] w-64 flex-shrink-0 flex-col rounded-lg border p-2.5 transition-colors ${
        isOver ? "border-ember-500 bg-ember-500/5" : "border-ink-800 bg-ink-900"
      }`}
    >
      <header className="mb-2.5 flex items-center gap-2 px-1">
        <span className={`h-2 w-2 rounded-full ${accent}`} />
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
          {STATUS_LABELS[status]}
        </h2>
        <span className="ml-auto rounded-full bg-ink-800 px-2 py-0.5 text-xs text-slate-500">
          {issues.length}
        </span>
      </header>

      <div className="flex-1 space-y-2.5">
        {issues.map((issue) => (
          <PersonalKanbanCard
            key={issue.id}
            issue={issue}
            project={projectsById.get(issue.project_id)}
          />
        ))}
        {issues.length === 0 && (
          <div className="flex min-h-20 items-center justify-center rounded-md border border-dashed border-ink-800 px-3 text-center text-xs text-slate-600">
            {status === "done" ? "Drop here to complete" : "No assigned tasks"}
          </div>
        )}
      </div>
    </section>
  );
}

export default function PersonalKanbanBoard({
  issues,
  projects,
  onMoveIssue,
}: {
  issues: IssueResponse[];
  projects: ProjectResponse[];
  onMoveIssue: (issueId: string, status: IssueStatus) => void;
}) {
  const [pendingCompletion, setPendingCompletion] = useState<IssueResponse | null>(null);
  const projectsById = useMemo(
    () => new Map(projects.map((project) => [project.id, project])),
    [projects],
  );

  function handleDragEnd(event: DragEndEvent) {
    if (!event.over) return;
    const issue = issues.find((candidate) => candidate.id === String(event.active.id));
    const status = String(event.over.id) as IssueStatus;
    if (!issue || issue.status === status || !COLUMNS.some((column) => column.status === status)) {
      return;
    }
    if (status === "done") {
      setPendingCompletion(issue);
      return;
    }
    onMoveIssue(issue.id, status);
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {COLUMNS.map((column) => (
          <PersonalKanbanColumn
            key={column.status}
            status={column.status}
            accent={column.accent}
            issues={issues.filter((issue) => issue.status === column.status).sort(compareCards)}
            projectsById={projectsById}
          />
        ))}
      </div>

      {pendingCompletion && (
        <Modal title="Complete this task?" onClose={() => setPendingCompletion(null)}>
          <p className="text-sm text-slate-400">
            <span className="text-slate-200">{pendingCompletion.title}</span> will be marked as
            done and removed from your pending board.
          </p>
          <ModalActions>
            <button
              onClick={() => setPendingCompletion(null)}
              className="rounded-md border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                onMoveIssue(pendingCompletion.id, "done");
                setPendingCompletion(null);
              }}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Complete task
            </button>
          </ModalActions>
        </Modal>
      )}
    </DndContext>
  );
}
