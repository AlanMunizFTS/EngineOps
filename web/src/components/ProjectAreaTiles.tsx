import type { AreaStatusResponse, ProjectAreaResponse } from "../api/client";

interface ProjectAreaTilesProps {
  areas: ProjectAreaResponse[];
  statusOptions: Record<string, AreaStatusResponse[]>;
  onStatusChange: (area: ProjectAreaResponse, statusId: string) => void;
}

export default function ProjectAreaTiles({
  areas,
  statusOptions,
  onStatusChange,
}: ProjectAreaTilesProps) {
  return (
    <section className="rounded-md border border-ink-800 bg-ink-900 p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-100">Areas</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {areas.map((area) => (
          <div
            key={area.id}
            className="rounded-md border border-ink-700 bg-ink-850 p-3 transition-colors hover:border-ember-500/40"
          >
            <p className="text-sm font-medium text-slate-100">{area.area_type.name}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-ember-500" />
              <select
                value={area.status.id}
                onChange={(e) => onStatusChange(area, e.target.value)}
                className="w-full appearance-none rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm text-slate-200 outline-none transition-colors focus:border-ember-500 focus:ring-1 focus:ring-ember-500"
              >
                {(statusOptions[area.area_type.id] ?? [area.status]).map((status) => (
                  <option key={status.id} value={status.id}>
                    {status.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
