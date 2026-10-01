import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  getProject,
  getProjectTimeline,
  listProjectMembers,
  type AuditLogEntryResponse,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import { listProjectTasks, type TaskResponse } from "../api/client_tasks";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import FileTree from "../components/FileTree";
import ProjectAbout from "../components/ProjectAbout";
import ProjectTabs from "../components/ProjectTabs";
import ScopeCard from "../components/ScopeCard";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [timeline, setTimeline] = useState<AuditLogEntryResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [treeVersion, setTreeVersion] = useState(0);

  useEffect(() => {
    if (token && projectId) void loadAll(token, projectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll(authToken: string, id: string) {
    try {
      const [projectData, timelineData, memberData, taskData] = await Promise.all([
        getProject(authToken, id),
        getProjectTimeline(authToken, id),
        listProjectMembers(authToken, id),
        listProjectTasks(authToken, id),
      ]);
      setProject(projectData);
      setTimeline(timelineData);
      setMembers(memberData);
      setTasks(taskData.filter((task) => task.parent_task_id === null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    }
  }

  if (!project) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-4">
          {error && <p className="text-sm text-red-400">{error}</p>}

          <section aria-label="Task metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              ["Open Tasks", tasks.filter((task) => task.status !== "done").length],
              ["Completed Tasks", tasks.filter((task) => task.status === "done").length],
              ["Overdue Tasks", tasks.filter((task) => task.schedule_status === "late" && task.status !== "done").length],
              ["Total Tasks", tasks.length],
            ].map(([label, value]) => <div key={label} className="rounded-md border border-ink-800 bg-ink-900 p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold text-slate-100">{value}</p></div>)}
          </section>

          <FileTree
            projectId={project.id}
            refreshKey={treeVersion}
            onChange={() => setTreeVersion((v) => v + 1)}
          />

          <ScopeCard
            projectId={project.id}
            refreshKey={treeVersion}
            onChange={() => setTreeVersion((v) => v + 1)}
          />
        </div>

        <ProjectAbout description={project.description} members={members} timeline={timeline} />
      </div>
    </AppShell>
  );
}
