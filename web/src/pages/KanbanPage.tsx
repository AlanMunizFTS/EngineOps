import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type ProjectResponse } from "../api/client";
import {
  getProjectKanbanBoard,
  listProjectIssues,
  updateIssueStatus,
  type IssueResponse,
  type IssueStatus,
  type KanbanBoardResponse,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import KanbanBoard from "../components/KanbanBoard";
import ProjectTabs from "../components/ProjectTabs";

export default function KanbanPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [board, setBoard] = useState<KanbanBoardResponse | null>(null);
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, boardData, issueData] = await Promise.all([
        getProject(token, projectId),
        getProjectKanbanBoard(token, projectId),
        listProjectIssues(token, projectId),
      ]);
      setProject(projectData);
      setBoard(boardData);
      setIssues(issueData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load kanban board");
    }
  }

  async function handleMoveIssue(issueId: string, status: IssueStatus) {
    if (!token) return;
    const previous = issues;
    setIssues((current) =>
      current.map((issue) => (issue.id === issueId ? { ...issue, status } : issue)),
    );
    try {
      await updateIssueStatus(token, issueId, status);
    } catch (err) {
      setIssues(previous);
      setError(err instanceof Error ? err.message : "Failed to move issue");
    }
  }

  if (!project || !board) {
    return (
      <AppShell>
        <p className="p-8 text-sm text-slate-500">{error ?? "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={project.name}>
      <ProjectTabs projectId={project.id} />

      <div className="p-6">
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <KanbanBoard
          columns={board.columns}
          issues={issues}
          projectId={project.id}
          onMoveIssue={handleMoveIssue}
        />
      </div>
    </AppShell>
  );
}
