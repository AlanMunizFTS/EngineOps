import { useState } from "react";

import {
  createPartNumber,
  createPieceCondition,
  createPieceLocation,
  createPieces,
  type PartNumberResponse,
  type PieceConditionResponse,
  type PieceLocationResponse,
  type PieceResponse,
  type PieceStatus,
} from "../api/client_pieces";

const inputClasses =
  "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500";

function InlineCreate({
  placeholder,
  onCreate,
}: {
  placeholder: string;
  onCreate: (name: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  async function submit() {
    if (!value.trim()) return;
    await onCreate(value.trim());
    setValue("");
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-ember-400 hover:text-ember-300"
      >
        + New
      </button>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <input
        autoFocus
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className={`${inputClasses} w-32`}
      />
      <button
        type="button"
        onClick={submit}
        className="text-xs text-ember-400 hover:text-ember-300"
      >
        Add
      </button>
    </div>
  );
}

export default function MaterialRegisterForm({
  token,
  projectId,
  partNumbers,
  conditions,
  locations,
  onCatalogsChanged,
  onPiecesCreated,
  onError,
}: {
  token: string;
  projectId: string;
  partNumbers: PartNumberResponse[];
  conditions: PieceConditionResponse[];
  locations: PieceLocationResponse[];
  onCatalogsChanged: () => Promise<void>;
  onPiecesCreated: (pieces: PieceResponse[]) => void;
  onError: (message: string) => void;
}) {
  const [partNumberId, setPartNumberId] = useState("");
  const [status, setStatus] = useState<PieceStatus>("ok");
  const [conditionIds, setConditionIds] = useState<string[]>([]);
  const [locationId, setLocationId] = useState("");
  const [notes, setNotes] = useState("");
  const [quantity, setQuantity] = useState(1);

  function toggleCondition(id: string) {
    setConditionIds((current) =>
      current.includes(id) ? current.filter((c) => c !== id) : [...current, id],
    );
  }

  async function handleSubmit() {
    if (!partNumberId) {
      onError("Select a part number before registering pieces");
      return;
    }
    try {
      const pieces = await createPieces(token, projectId, {
        part_number_id: partNumberId,
        status,
        condition_ids: conditionIds,
        location_id: locationId || null,
        notes: notes || null,
        quantity,
      });
      onPiecesCreated(pieces);
      setNotes("");
      setQuantity(1);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to register pieces");
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-ink-800 bg-ink-900 p-4">
      <h3 className="text-sm font-semibold text-slate-200">Register piece(s)</h3>
      <p className="text-xs text-slate-500">
        Measurements are set per piece afterward, from the table below - each piece gets its own
        values, even when registered in a batch.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={partNumberId}
          onChange={(e) => setPartNumberId(e.target.value)}
          className={inputClasses}
        >
          <option value="">Select part number</option>
          {partNumbers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <InlineCreate
          placeholder="Part number"
          onCreate={async (name) => {
            const created = await createPartNumber(token, projectId, name);
            await onCatalogsChanged();
            setPartNumberId(created.id);
          }}
        />

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as PieceStatus)}
          className={inputClasses}
        >
          <option value="ok">OK</option>
          <option value="nok">NOK</option>
        </select>

        <select
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          className={inputClasses}
        >
          <option value="">No location</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </select>
        <InlineCreate
          placeholder="Location"
          onCreate={async (name) => {
            const created = await createPieceLocation(token, projectId, name);
            await onCatalogsChanged();
            setLocationId(created.id);
          }}
        />

        <input
          type="number"
          min={1}
          max={1000}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
          className={`${inputClasses} w-20`}
          title="Quantity"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">Conditions:</span>
        {conditions.map((condition) => (
          <label key={condition.id} className="flex items-center gap-1 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={conditionIds.includes(condition.id)}
              onChange={() => toggleCondition(condition.id)}
            />
            {condition.name}
          </label>
        ))}
        <InlineCreate
          placeholder="Condition"
          onCreate={async (name) => {
            const created = await createPieceCondition(token, projectId, name);
            await onCatalogsChanged();
            setConditionIds((current) => [...current, created.id]);
          }}
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className={`${inputClasses} flex-1`}
        />
        <button
          type="button"
          onClick={handleSubmit}
          className="rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
        >
          Register
        </button>
      </div>
    </div>
  );
}
