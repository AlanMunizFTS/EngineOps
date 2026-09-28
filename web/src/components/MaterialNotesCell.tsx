import { useState } from "react";

import { updatePiece, type PieceResponse } from "../api/client_pieces";

export default function MaterialNotesCell({
  token,
  piece,
  onSaved,
}: {
  token: string;
  piece: PieceResponse;
  onSaved: (piece: PieceResponse) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(piece.notes ?? "");
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setValue(piece.notes ?? "");
    setEditing(true);
  }

  async function save() {
    if (value === (piece.notes ?? "")) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await updatePiece(token, piece.id, {
        status: piece.overall_status,
        location_id: piece.location_id,
        notes: value.trim() || null,
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
      <input
        autoFocus
        type="text"
        disabled={saving}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === "Enter") save();
          if (e.key === "Escape") setEditing(false);
        }}
        className="w-full rounded-md border border-ember-500 bg-ink-800 px-2 py-1 text-xs text-slate-100 outline-none"
      />
    );
  }

  return (
    <button
      type="button"
      onClick={startEdit}
      title="Click to edit notes"
      className="w-full rounded px-1 py-0.5 text-left text-xs text-slate-400 hover:bg-ink-800 hover:text-slate-200"
    >
      {piece.notes ?? "—"}
    </button>
  );
}
