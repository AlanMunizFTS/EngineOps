import type {
  MeasurementTypeResponse,
  PartNumberResponse,
  PieceConditionResponse,
  PieceLocationResponse,
  PieceStatus,
} from "../api/client_pieces";

export interface MaterialFilterState {
  partNumberId: string;
  status: PieceStatus | "";
  conditionIds: string[];
  locationId: string;
  measurementTypeId: string;
  measurementMin: string;
  measurementMax: string;
}

const selectClasses =
  "rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-200 outline-none focus:border-ember-500";

export default function MaterialFilterBar({
  partNumbers,
  conditions,
  locations,
  measurementTypes,
  filters,
  onChange,
  totalCount,
  countsByLocation,
}: {
  partNumbers: PartNumberResponse[];
  conditions: PieceConditionResponse[];
  locations: PieceLocationResponse[];
  measurementTypes: MeasurementTypeResponse[];
  filters: MaterialFilterState;
  onChange: (next: MaterialFilterState) => void;
  totalCount: number;
  countsByLocation: { name: string; count: number }[];
}) {
  const selectedMeasurementType = measurementTypes.find(
    (t) => t.id === filters.measurementTypeId,
  );

  function toggleCondition(conditionId: string) {
    const next = filters.conditionIds.includes(conditionId)
      ? filters.conditionIds.filter((id) => id !== conditionId)
      : [...filters.conditionIds, conditionId];
    onChange({ ...filters, conditionIds: next });
  }

  return (
    <div className="space-y-3 rounded-md border border-ink-800 bg-ink-900 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={filters.partNumberId}
          onChange={(e) => onChange({ ...filters, partNumberId: e.target.value })}
          className={selectClasses}
        >
          <option value="">All part numbers</option>
          {partNumbers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>

        <select
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value as PieceStatus | "" })}
          className={selectClasses}
        >
          <option value="">All statuses</option>
          <option value="ok">OK</option>
          <option value="nok">NOK</option>
        </select>

        <select
          value={filters.locationId}
          onChange={(e) => onChange({ ...filters, locationId: e.target.value })}
          className={selectClasses}
        >
          <option value="">All locations</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </select>

        <div className="ml-auto text-right text-sm text-slate-400">
          <span className="font-semibold text-slate-100">{totalCount}</span> pieces
          {countsByLocation.length > 0 && (
            <span className="ml-2 text-xs text-slate-500">
              ({countsByLocation.map((c) => `${c.name}: ${c.count}`).join(", ")})
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {conditions.map((condition) => {
          const active = filters.conditionIds.includes(condition.id);
          return (
            <button
              key={condition.id}
              onClick={() => toggleCondition(condition.id)}
              className={`rounded-full border px-2 py-0.5 text-xs font-medium transition-colors ${
                active
                  ? "border-ember-500 bg-ember-500/10 text-ember-400"
                  : "border-ink-700 text-slate-400 hover:border-ink-600"
              }`}
            >
              {condition.name}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={filters.measurementTypeId}
          onChange={(e) =>
            onChange({ ...filters, measurementTypeId: e.target.value, measurementMin: "", measurementMax: "" })
          }
          className={selectClasses}
        >
          <option value="">No measurement filter</option>
          {measurementTypes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.unit})
            </option>
          ))}
        </select>
        {selectedMeasurementType && (
          <>
            <input
              type="number"
              step="any"
              placeholder={`min (${selectedMeasurementType.unit})`}
              value={filters.measurementMin}
              onChange={(e) => onChange({ ...filters, measurementMin: e.target.value })}
              className="w-32 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
            <input
              type="number"
              step="any"
              placeholder={`max (${selectedMeasurementType.unit})`}
              value={filters.measurementMax}
              onChange={(e) => onChange({ ...filters, measurementMax: e.target.value })}
              className="w-32 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
            />
          </>
        )}
      </div>
    </div>
  );
}
