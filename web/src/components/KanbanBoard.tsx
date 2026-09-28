import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { ProjectMemberDetailResponse } from "../api/client";
import type { IssueResponse, IssueStatus, KanbanColumnResponse } from "../api/client_issues";
import { PriorityBadge, PriorityScoreChip, STATUS_LABELS } from "./IssueBadges";
import { PlusIcon, TrashIcon } from "./icons";
import Modal, { ModalActions } from "./Modal";

const ALL_STATUSES: IssueStatus[] = ["backlog", "todo", "in_progress", "in_review", "done"];

// Highest Priority Score first, so the card that most needs attention is
// always the top one in its column. Cards with no score (done, or no
// due_date) sort last regardless of direction - there's nothing to rank
// them by. Ties (e.g. two cards both scored 10 while overdue) fall back to
// whichever has fewer days left until its due_date, so the more time-
// critical of the two still surfaces above the other.
function compareCards(a: IssueResponse, b: IssueResponse): number {
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

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function KanbanCard({
  issue,
  projectId,
  assigneeName,
}: {
  issue: IssueResponse;
  projectId: string;
  assigneeName: string | null;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: issue.id,
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
        to={`/projects/${projectId}/issues/${issue.id}`}
        onClick={(e) => isDragging && e.preventDefault()}
        className="text-slate-100 hover:text-ember-400"
      >
        {issue.title}
      </Link>
      <div className="flex items-center gap-1">
        <PriorityBadge priority={issue.priority} />
        <span className="text-xs text-slate-500">{issue.issue_type}</span>
        {issue.priority_score !== null && (
          <span className="ml-auto">
            <PriorityScoreChip score={issue.priority_score} />
          </span>
        )}
        {assigneeName && (
          <span
            title={assigneeName}
            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-700 text-[10px] font-medium text-slate-300 ${
              issue.priority_score === null ? "ml-auto" : ""
            }`}
          >
            {initials(assigneeName)}
          </span>
        )}
      </div>
    </div>
  );
}

function StatusCheckboxes({
  selected,
  onChange,
}: {
  selected: IssueStatus[];
  onChange: (statuses: IssueStatus[]) => void;
}) {
  function toggle(status: IssueStatus) {
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
  issues,
  projectId,
  assigneeNameById,
  onRenameColumn,
  onDeleteColumn,
}: {
  column: KanbanColumnResponse;
  issues: IssueResponse[];
  projectId: string;
  assigneeNameById: Map<string, string>;
  onRenameColumn: (columnId: string, name: string, mapsToStatuses: IssueStatus[]) => void;
  onDeleteColumn: (columnId: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(column.name);
  const [statuses, setStatuses] = useState<IssueStatus[]>(column.maps_to_statuses);

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
              {issues.length}
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
      <div className="min-h-16 flex-1 space-y-2">
        {issues.map((issue) => (
          <KanbanCard
            key={issue.id}
            issue={issue}
            projectId={projectId}
            assigneeName={issue.assignee_id ? (assigneeNameById.get(issue.assignee_id) ?? null) : null}
          />
        ))}
      </div>
    </div>
  );
}

function NewColumnForm({
  onCreate,
}: {
  onCreate: (name: string, mapsToStatuses: IssueStatus[]) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [statuses, setStatuses] = useState<IssueStatus[]>([]);

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
  issues,
  members,
  projectId,
  onMoveIssue,
  onCreateColumn,
  onRenameColumn,
  onDeleteColumn,
}: {
  columns: KanbanColumnResponse[];
  issues: IssueResponse[];
  members: ProjectMemberDetailResponse[];
  projectId: string;
  onMoveIssue: (issueId: string, status: IssueStatus) => void;
  onCreateColumn: (name: string, mapsToStatuses: IssueStatus[]) => void;
  onRenameColumn: (columnId: string, name: string, mapsToStatuses: IssueStatus[]) => void;
  onDeleteColumn: (columnId: string) => void;
}) {
  const [pendingMove, setPendingMove] = useState<{ issueId: string; status: IssueStatus } | null>(
    null,
  );
  const assigneeNameById = useMemo(
    () => new Map(members.map((member) => [member.user_id, member.full_name])),
    [members],
  );

  // Parent issues track progress via the Schedule rollup, not a status of
  // their own - they never show up as Kanban cards.
  const boardIssues = useMemo(() => {
    const parentIds = new Set(
      issues.map((issue) => issue.parent_issue_id).filter((id): id is string => id !== null),
    );
    return issues.filter((issue) => !parentIds.has(issue.id));
  }, [issues]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const issueId = String(active.id);
    const targetColumn = columns.find((c) => c.id === over.id);
    if (!targetColumn || targetColumn.maps_to_statuses.length === 0) return;
    const targetStatus = targetColumn.maps_to_statuses[0];
    const issue = boardIssues.find((i) => i.id === issueId);
    if (!issue || issue.status === targetStatus) return;
    if (targetStatus === "done") {
      setPendingMove({ issueId, status: targetStatus });
      return;
    }
    onMoveIssue(issueId, targetStatus);
  }

  const pendingIssue = pendingMove ? boardIssues.find((i) => i.id === pendingMove.issueId) : null;

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {columns.map((column) => (
          <KanbanColumnView
            key={column.id}
            column={column}
            issues={boardIssues
              .filter((issue) => column.maps_to_statuses.includes(issue.status))
              .sort(compareCards)}
            projectId={projectId}
            assigneeNameById={assigneeNameById}
            onRenameColumn={onRenameColumn}
            onDeleteColumn={onDeleteColumn}
          />
        ))}
        <NewColumnForm onCreate={onCreateColumn} />
      </div>

      {pendingMove && (
        <Modal title="Close this activity?" onClose={() => setPendingMove(null)}>
          <p className="text-sm text-slate-400">
            Marking{" "}
            <span className="text-slate-200">{pendingIssue?.title ?? "this issue"}</span> as done
            will record the close date. This can be reopened later by changing its status again.
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
                onMoveIssue(pendingMove.issueId, pendingMove.status);
                setPendingMove(null);
              }}
              className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
            >
              Close activity
            </button>
          </ModalActions>
        </Modal>
      )}
    </DndContext>
  );
}
