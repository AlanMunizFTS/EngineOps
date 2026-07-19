import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import { listProjects, type ProjectResponse } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import ProjectSidebar from "./ProjectSidebar";
import TopBar from "./TopBar";

export default function AppShell({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const { projectId: activeProjectId } = useParams<{ projectId?: string }>();

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [isNavExpanded, setIsNavExpanded] = useState(false);

  useEffect(() => {
    if (!token) return;
    listProjects(token)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [token]);

  return (
    <div className="flex min-h-screen flex-col bg-ink-950">
      <TopBar projects={projects} onToggleSidebar={() => setIsNavExpanded((prev) => !prev)} />
      <div className="flex min-h-0 flex-1">
        <ProjectSidebar
          projects={projects}
          activeProjectId={activeProjectId}
          isExpanded={isNavExpanded}
        />
        <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
