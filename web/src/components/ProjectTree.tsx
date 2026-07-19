import { Link } from "react-router-dom";

import type { ProjectResponse } from "../api/client";

function ProjectIcon({ name }: { name: string }) {
  return (
    <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-ink-700 text-[10px] font-semibold text-slate-300">
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

export default function ProjectTree({
  projects,
  activeProjectId,
}: {
  projects: ProjectResponse[];
  activeProjectId?: string;
}) {
  return (
    <div className="space-y-0.5">
      {projects.map((project) => {
        const isActive = project.id === activeProjectId;
        return (
          <Link
            key={project.id}
            to={`/projects/${project.id}`}
            className={`flex items-center gap-2 truncate rounded-md px-2 py-1.5 text-sm transition-colors ${
              isActive ? "bg-ember-500/10 text-ember-400" : "text-slate-300 hover:bg-ink-800"
            }`}
          >
            <ProjectIcon name={project.name} />
            <span className="truncate">{project.name}</span>
          </Link>
        );
      })}
    </div>
  );
}
