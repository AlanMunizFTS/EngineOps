import { useState } from "react";

import {
  createMeasurementType,
  deleteMeasurementType,
  updateMeasurementType,
  type MeasurementTypeResponse,
  type PartNumberResponse,
  type PieceConditionResponse,
  type PieceStatus,
} from "../api/client_pieces";
import Modal, { ModalActions } from "./Modal";

const inputClasses =
  "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500";

function scopeDescription(
  type: MeasurementTypeResponse,
  partNumberNameById: Map<string, string>,
  conditionNameById: Map<string, string>,
): string {
  const parts = [
    type.part_number_id
      ? (partNumberNameById.get(type.part_number_id) ?? "Unknown part")
      : "Any part number",
    type.status ? type.status.toUpperCase() : "Any status",
    type.condition_id
      ? (conditionNameById.get(type.condition_id) ?? "Unknown condition")
      : "Any condition",
  ];
  return parts.join(" · ");
}

const EMPTY_FORM = { name: "", unit: "mm", partNumberId: "", status: "" as PieceStatus | "", conditionId: "" };

export default function MeasurementTypeModal({
  token,
  projectId,
  partNumbers,
  conditions,
  measurementTypes,
  onClose,
  onChanged,
}: {
  token: string;
  projectId: string;
  partNumbers: PartNumberResponse[];
  conditions: PieceConditionResponse[];
  measurementTypes: MeasurementTypeResponse[];
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  const partNumberNameById = new Map(partNumbers.map((p) => [p.id, p.name]));
  const conditionNameById = new Map(conditions.map((c) => [c.id, c.name]));

  function startEdit(type: MeasurementTypeResponse) {
    setEditingId(type.id);
    setForm({
      name: type.name,
      unit: type.unit,
      partNumberId: type.part_number_id ?? "",
      status: type.status ?? "",
      conditionId: type.condition_id ?? "",
    });
    setError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setError(null);
  }

  async function handleDelete(type: MeasurementTypeResponse) {
    if (!window.confirm(`Delete "${type.name}"? Existing measured values of this type on any piece will be removed too.`)) {
      return;
    }
    try {
      await deleteMeasurementType(token, type.id);
      if (editingId === type.id) cancelEdit();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete measurement type");
    }
  }

  async function handleSubmit() {
    if (!form.name.trim() || !form.unit.trim()) {
      setError("Name and unit are required");
      return;
    }
    const fields = {
      name: form.name.trim(),
      unit: form.unit.trim(),
      part_number_id: form.partNumberId || null,
      status: form.status || null,
      condition_id: form.conditionId || null,
    };
    try {
      if (editingId) {
        await updateMeasurementType(token, editingId, fields);
      } else {
        await createMeasurementType(token, projectId, fields);
      }
      cancelEdit();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save measurement type");
    }
  }

  return (
    <Modal title="Configure measurements" onClose={onClose}>
      <div className="space-y-4">
        {measurementTypes.length > 0 && (
          <div className="space-y-1 border-b border-ink-800 pb-3">
            {measurementTypes.map((type) => (
              <div key={type.id} className="flex items-center justify-between gap-2 text-xs">
                <div>
                  <span className="text-slate-200">
                    {type.name} ({type.unit})
                  </span>
                  <span className="ml-2 text-slate-500">
                    {scopeDescription(type, partNumberNameById, conditionNameById)}
                  </span>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => startEdit(type)}
                    className="text-ember-400 hover:text-ember-300"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(type)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-xs text-red-400">{error}</p>}

        <div className="space-y-2">
          {editingId && (
            <p className="text-xs text-ember-400">
              Editing "{measurementTypes.find((t) => t.id === editingId)?.name}"
            </p>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Name (e.g. Split Width)"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className={`${inputClasses} flex-1`}
            />
            <input
              type="text"
              placeholder="Unit (e.g. mm)"
              value={form.unit}
              onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
              className={`${inputClasses} w-20`}
            />
          </div>

          <label className="block text-xs text-slate-500">
            Part number
            <select
              value={form.partNumberId}
              onChange={(e) => setForm((f) => ({ ...f, partNumberId: e.target.value }))}
              className={`${inputClasses} mt-1 w-full`}
            >
              <option value="">Any part number</option>
              {partNumbers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs text-slate-500">
            Status
            <select
              value={form.status}
              onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as PieceStatus | "" }))}
              className={`${inputClasses} mt-1 w-full`}
            >
              <option value="">Any status</option>
              <option value="ok">OK only</option>
              <option value="nok">NOK only</option>
            </select>
          </label>

          <label className="block text-xs text-slate-500">
            Condition
            <select
              value={form.conditionId}
              onChange={(e) => setForm((f) => ({ ...f, conditionId: e.target.value }))}
              className={`${inputClasses} mt-1 w-full`}
            >
              <option value="">Any condition</option>
              {conditions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <ModalActions>
        {editingId && (
          <button
            type="button"
            onClick={cancelEdit}
            className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 hover:border-ink-600"
          >
            Cancel edit
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-slate-300 hover:border-ink-600"
        >
          Close
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
        >
          {editingId ? "Save changes" : "Add measurement type"}
        </button>
      </ModalActions>
    </Modal>
  );
}
