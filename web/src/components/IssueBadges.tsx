import type {
  IssuePriority,
  IssueStatus,
  LabelResponse,
  ScheduleStatus,
  Urgency,
} from "../api/client_issues";

export const STATUS_LABELS: Record<IssueStatus, string> = {
  backlog: "Backlog",
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
};

const STATUS_COLORS: Record<IssueStatus, string> = {
  backlog: "bg-slate-500/10 text-slate-400",
  todo: "bg-sky-500/10 text-sky-400",
  in_progress: "bg-amber-500/10 text-amber-400",
  in_review: "bg-violet-500/10 text-violet-400",
  done: "bg-emerald-500/10 text-emerald-400",
};

export const PRIORITY_COLORS: Record<IssuePriority, string> = {
  low: "bg-slate-500/10 text-slate-400",
  medium: "bg-sky-500/10 text-sky-400",
  high: "bg-amber-500/10 text-amber-400",
  urgent: "bg-red-500/10 text-red-400",
};

export function StatusBadge({ status }: { status: IssueStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: IssuePriority }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLORS[priority]}`}>
      {priority}
    </span>
  );
}

const URGENCY_COLORS: Record<Urgency, string> = {
  low: "bg-slate-500/10 text-slate-400",
  medium: "bg-amber-500/10 text-amber-400",
  high: "bg-red-500/10 text-red-400",
};

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${URGENCY_COLORS[urgency]}`}>
      {urgency}
    </span>
  );
}

const SCHEDULE_STATUS_LABELS: Record<ScheduleStatus, string> = {
  closed: "CLOSED",
  on_time: "ON TIME",
  late: "LATE",
};

const SCHEDULE_STATUS_COLORS: Record<ScheduleStatus, string> = {
  closed: "bg-emerald-500/10 text-emerald-400",
  on_time: "bg-sky-500/10 text-sky-400",
  late: "bg-red-500/10 text-red-400",
};

export function ScheduleStatusBadge({ status }: { status: ScheduleStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${SCHEDULE_STATUS_COLORS[status]}`}
    >
      {SCHEDULE_STATUS_LABELS[status]}
    </span>
  );
}

export function PriorityScoreChip({ score }: { score: number }) {
  const color =
    score >= 9
      ? "bg-red-500/10 text-red-400"
      : score >= 6
        ? "bg-amber-500/10 text-amber-400"
        : score >= 3
          ? "bg-sky-500/10 text-sky-400"
          : "bg-slate-500/10 text-slate-400";
  return (
    <span
      title="Priority Score (Urgency x Importance, 1-10)"
      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}
    >
      {score}
    </span>
  );
}

export function LabelChip({ label }: { label: LabelResponse }) {
  return (
    <span
      className="rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{ borderColor: label.color, color: label.color }}
    >
      {label.name}
    </span>
  );
}
