import { useMemo, useState } from "react";

import {
  setPieceMeasurement,
  type MeasurementTypeResponse,
  type PieceResponse,
} from "../api/client_pieces";
import Modal, { ModalActions } from "./Modal";

const inputClasses =
  "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500";

function applicableMeasurementTypes(
  piece: PieceResponse,
  measurementTypes: MeasurementTypeResponse[],
): MeasurementTypeResponse[] {
  const conditionIds = new Set(piece.conditions.map((c) => c.id));
  return measurementTypes.filter(
    (t) =>
      (!t.part_number_id || t.part_number_id === piece.part_number_id) &&
      (!t.status || t.status === piece.overall_status) &&
      (!t.condition_id || conditionIds.has(t.condition_id)),
  );
}

export default function PieceMeasurementsModal({
  token,
  piece,
  measurementTypes,
  onClose,
  onSaved,
}: {
  token: string;
  piece: PieceResponse;
  measurementTypes: MeasurementTypeResponse[];
  onClose: () => void;
  onSaved: (piece: PieceResponse) => void;
}) {
  const applicableTypes = useMemo(
    () => applicableMeasurementTypes(piece, measurementTypes),
    [piece, measurementTypes],
  );
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      applicableTypes.map((t) => [
        t.id,
        piece.measurements.find((m) => m.measurement_type_id === t.id)?.value ?? "",
      ]),
    ),
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      let latest = piece;
      for (const type of applicableTypes) {
        const value = values[type.id]?.trim();
        const existing = piece.measurements.find((m) => m.measurement_type_id === type.id);
        if (!value || value === existing?.value) continue;
        latest = await setPieceMeasurement(token, piece.id, type.id, value);
      }
      onSaved(latest);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save measurements");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={`Measurements - ${piece.tracking_number}`} onClose={onClose}>
      <div className="space-y-3">
        {applicableTypes.length === 0 ? (
          <p className="text-sm text-slate-500">
            No measurement types apply to this piece's part number/status/conditions. Configure
            one from "Configure measurements".
          </p>
        ) : (
          applicableTypes.map((type) => (
            <label key={type.id} className="block text-xs text-slate-500">
              {type.name} ({type.unit})
              <input
                type="number"
                step="any"
                value={values[type.id] ?? ""}
                onChange={(e) => setValues((current) => ({ ...current, [type.id]: e.target.value }))}
                className={`${inputClasses} mt-1 w-full`}
              />
            </label>
          ))
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      <ModalActions>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 hover:border-ink-600"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={saving || applicableTypes.length === 0}
          onClick={handleSave}
          className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </ModalActions>
    </Modal>
  );
}
