import { DndContext, type DragEndEvent, useDraggable, useDroppable } from "@dnd-kit/core";
import { Link } from "react-router-dom";

import type { IssueResponse, IssueStatus, KanbanColumnResponse } from "../api/client_issues";
import { PriorityBadge } from "./IssueBadges";

function KanbanCard({ issue, projectId }: { issue: IssueResponse; projectId: string }) {
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
      </div>
    </div>
  );
}

function KanbanColumnView({
  column,
  issues,
  projectId,
}: {
  column: KanbanColumnResponse;
  issues: IssueResponse[];
  projectId: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.maps_to_status });

  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 flex-shrink-0 flex-col rounded-md border p-2 ${
        isOver ? "border-ember-500 bg-ember-500/5" : "border-ink-800 bg-ink-900"
      }`}
    >
      <h3 className="mb-2 flex items-center justify-between px-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {column.name}
        <span className="rounded-full bg-ink-800 px-1.5 py-0.5 text-slate-500">
          {issues.length}
        </span>
      </h3>
      <div className="min-h-16 flex-1 space-y-2">
        {issues.map((issue) => (
          <KanbanCard key={issue.id} issue={issue} projectId={projectId} />
        ))}
      </div>
    </div>
  );
}

export default function KanbanBoard({
  columns,
  issues,
  projectId,
  onMoveIssue,
}: {
  columns: KanbanColumnResponse[];
  issues: IssueResponse[];
  projectId: string;
  onMoveIssue: (issueId: string, status: IssueStatus) => void;
}) {
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const issueId = String(active.id);
    const targetStatus = over.id as IssueStatus;
    const issue = issues.find((i) => i.id === issueId);
    if (issue && issue.status !== targetStatus) {
      onMoveIssue(issueId, targetStatus);
    }
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {columns.map((column) => (
          <KanbanColumnView
            key={column.id}
            column={column}
            issues={issues.filter((issue) => issue.status === column.maps_to_status)}
            projectId={projectId}
          />
        ))}
      </div>
    </DndContext>
  );
}
