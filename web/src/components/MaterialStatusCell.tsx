import { useState } from "react";

import { updatePiece, type PieceResponse, type PieceStatus } from "../api/client_pieces";
import { PieceStatusBadge } from "./MaterialBadges";

export default function MaterialStatusCell({
  token,
  piece,
  onSaved,
}: {
  token: string;
  piece: PieceResponse;
  onSaved: (piece: PieceResponse) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleChange(status: PieceStatus) {
    if (status === piece.overall_status) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await updatePiece(token, piece.id, {
        status,
        location_id: piece.location_id,
        notes: piece.notes,
        condition_ids: piece.conditions.map((c) => c.id),
      });
      onSaved(updated);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  }

  if (editing) {
    return (
      <select
        autoFocus
        disabled={saving}
        value={piece.overall_status}
        onChange={(e) => handleChange(e.target.value as PieceStatus)}
        onBlur={() => setEditing(false)}
        className="rounded-md border border-ember-500 bg-ink-800 px-2 py-1 text-xs text-slate-100 outline-none"
      >
        <option value="ok">OK</option>
        <option value="nok">NOK</option>
      </select>
    );
  }

  return (
    <button type="button" onClick={() => setEditing(true)} title="Click to change status">
      <PieceStatusBadge status={piece.overall_status} />
    </button>
  );
}
