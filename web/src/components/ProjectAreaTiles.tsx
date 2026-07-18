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
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Areas</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {areas.map((area) => (
          <div key={area.id} className="rounded border border-slate-200 p-4">
            <p className="text-sm font-medium text-slate-900">{area.area_type.name}</p>
            <select
              value={area.status.id}
              onChange={(e) => onStatusChange(area, e.target.value)}
              className="mt-2 w-full rounded border border-slate-300 px-2 py-1 text-sm"
            >
              {(statusOptions[area.area_type.id] ?? [area.status]).map((status) => (
                <option key={status.id} value={status.id}>
                  {status.name}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </section>
  );
}
