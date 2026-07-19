import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  listAreaStatuses,
  listProjectAreas,
  type AreaStatusResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function ProjectPhasesSidebar({ projectId }: { projectId: string }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const viewingPhaseId = searchParams.get("phase");

  const [currentPhaseId, setCurrentPhaseId] = useState<string | undefined>(undefined);
  const [statuses, setStatuses] = useState<AreaStatusResponse[]>([]);

  useEffect(() => {
    if (!token) return;
    listProjectAreas(token, projectId).then(async (areas) => {
      const current = areas[0];
      setCurrentPhaseId(current?.status.id);
      if (current) {
        setStatuses(await listAreaStatuses(token, current.area_type.id));
      }
    });
  }, [token, projectId]);

  if (statuses.length === 0) return null;

  return (
    <div className="mt-4 border-t border-ink-800 pt-3">
      <h2 className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Phases
      </h2>
      <nav className="space-y-0.5">
        {statuses.map((status) => {
          const isCurrent = status.id === currentPhaseId;
          const isViewing = status.id === viewingPhaseId;
          return (
            <button
              key={status.id}
              onClick={() => navigate(`/projects/${projectId}?phase=${status.id}`)}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                isViewing
                  ? "bg-ember-500/10 text-ember-400"
                  : "text-slate-300 hover:bg-ink-800 hover:text-slate-100"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  isCurrent ? "bg-ember-500" : "bg-ink-600"
                }`}
              />
              <span className="truncate">{status.name}</span>
              {isCurrent && (
                <span className="ml-auto flex-shrink-0 text-[10px] text-slate-500">current</span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
