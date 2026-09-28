import type { PieceConditionResponse, PieceStatus } from "../api/client_pieces";

const STATUS_COLORS: Record<PieceStatus, string> = {
  ok: "bg-emerald-500/10 text-emerald-400",
  nok: "bg-red-500/10 text-red-400",
};

export function PieceStatusBadge({ status }: { status: PieceStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status]}`}>
      {status.toUpperCase()}
    </span>
  );
}

export function ConditionChip({ condition }: { condition: PieceConditionResponse }) {
  return (
    <span className="rounded-full border border-ink-600 px-2 py-0.5 text-xs font-medium text-slate-300">
      {condition.name}
    </span>
  );
}
