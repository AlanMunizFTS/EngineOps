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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    if (!token) return;
    listProjects(token)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [token]);

  return (
    <div className="flex min-h-screen bg-ink-950">
      {isSidebarOpen && <ProjectSidebar projects={projects} activeProjectId={activeProjectId} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar projects={projects} onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
