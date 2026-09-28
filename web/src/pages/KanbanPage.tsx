import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import {
  getProject,
  listProjectMembers,
  type ProjectMemberDetailResponse,
  type ProjectResponse,
} from "../api/client";
import {
  createKanbanBoard,
  createKanbanColumn,
  deleteKanbanBoard,
  deleteKanbanColumn,
  listKanbanBoards,
  listProjectIssues,
  renameKanbanBoard,
  updateIssueStatus,
  updateKanbanColumn,
  type IssueResponse,
  type IssueStatus,
  type KanbanBoardResponse,
} from "../api/client_issues";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/AppShell";
import KanbanBoard from "../components/KanbanBoard";
import ProjectTabs from "../components/ProjectTabs";
import { PlusIcon, TrashIcon } from "../components/icons";

const UNASSIGNED_FILTER_VALUE = "__unassigned__";

export default function KanbanPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [boards, setBoards] = useState<KanbanBoardResponse[]>([]);
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);
  const [issues, setIssues] = useState<IssueResponse[]>([]);
  const [members, setMembers] = useState<ProjectMemberDetailResponse[]>([]);
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [showNewBoard, setShowNewBoard] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && projectId) void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  async function loadAll() {
    if (!token || !projectId) return;
    try {
      const [projectData, boardData, issueData, memberData] = await Promise.all([
        getProject(token, projectId),
        listKanbanBoards(token, projectId),
        listProjectIssues(token, projectId),
        listProjectMembers(token, projectId),
      ]);
      setProject(projectData);
      setBoards(boardData);
      setIssues(issueData);
      setMembers(memberData);
      setActiveBoardId((current) =>
        current && boardData.some((b) => b.id === current) ? current : (boardData[0]?.id ?? null),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load kanban board");
    }
  }

  const filteredIssues = useMemo(() => {
    if (!assigneeFilter) return issues;
    if (assigneeFilter === UNASSIGNED_FILTER_VALUE) {
      return issues.filter((issue) => issue.assignee_id === null);
    }
    return issues.filter((issue) => issue.assignee_id === assigneeFilter);
  }, [issues, assigneeFilter]);

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

  async function handleCreateBoard() {
    if (!token || !projectId || !newBoardName.trim()) return;
    try {
      const board = await createKanbanBoard(token, projectId, newBoardName.trim());
      setNewBoardName("");
      setShowNewBoard(false);
      setBoards((current) => [...current, board]);
      setActiveBoardId(board.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create board");
    }
  }

  async function handleRenameBoard(boardId: string, name: string) {
    if (!token) return;
    try {
      const updated = await renameKanbanBoard(token, boardId, name);
      setBoards((current) => current.map((b) => (b.id === boardId ? updated : b)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename board");
    }
  }

  async function handleDeleteBoard(boardId: string) {
    if (!token) return;
    if (!window.confirm("Delete this board? Its columns will be removed too.")) return;
    try {
      await deleteKanbanBoard(token, boardId);
      setBoards((current) => {
        const remaining = current.filter((b) => b.id !== boardId);
        setActiveBoardId(remaining[0]?.id ?? null);
        return remaining;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete board");
    }
  }

  async function handleCreateColumn(name: string, mapsToStatuses: IssueStatus[]) {
    if (!token || !activeBoardId) return;
    try {
      const column = await createKanbanColumn(token, activeBoardId, name, mapsToStatuses);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId ? { ...b, columns: [...b.columns, column] } : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create column");
    }
  }

  async function handleRenameColumn(columnId: string, name: string, mapsToStatuses: IssueStatus[]) {
    if (!token || !activeBoardId) return;
    try {
      const updated = await updateKanbanColumn(token, columnId, name, mapsToStatuses);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId
            ? { ...b, columns: b.columns.map((c) => (c.id === columnId ? updated : c)) }
            : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update column");
    }
  }

  async function handleDeleteColumn(columnId: string) {
    if (!token || !activeBoardId) return;
    if (!window.confirm("Delete this column?")) return;
    try {
      await deleteKanbanColumn(token, columnId);
      setBoards((current) =>
        current.map((b) =>
          b.id === activeBoardId
            ? { ...b, columns: b.columns.filter((c) => c.id !== columnId) }
            : b,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete column");
    }
  }

  const activeBoard = boards.find((b) => b.id === activeBoardId) ?? null;

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

      <div className="p-6">
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <div className="mb-4 flex flex-wrap items-center gap-2">
          {boards.map((board) => (
            <div key={board.id} className="group flex items-center">
              <button
                onClick={() => setActiveBoardId(board.id)}
                onDoubleClick={() => {
                  const name = window.prompt("Rename board", board.name);
                  if (name && name.trim() && name.trim() !== board.name) {
                    void handleRenameBoard(board.id, name.trim());
                  }
                }}
                title="Double-click to rename"
                className={`rounded-l-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                  board.id === activeBoardId
                    ? "border-ember-500 bg-ember-500/10 text-ember-400"
                    : "border-ink-700 bg-ink-850 text-slate-300 hover:border-ink-600"
                }`}
              >
                {board.name}
              </button>
              {boards.length > 1 && (
                <button
                  onClick={() => handleDeleteBoard(board.id)}
                  title="Delete board"
                  className={`rounded-r-md border border-l-0 px-1.5 py-1.5 text-slate-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100 ${
                    board.id === activeBoardId
                      ? "border-ember-500 bg-ember-500/10"
                      : "border-ink-700 bg-ink-850"
                  }`}
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}

          {showNewBoard ? (
            <div className="flex items-center gap-1">
              <input
                autoFocus
                type="text"
                placeholder="Board name"
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateBoard()}
                className="rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateBoard}
                className="rounded-md bg-ember-500 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowNewBoard(true)}
              className="flex items-center gap-1 rounded-md border border-dashed border-ink-700 px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:border-ink-600 hover:text-slate-300"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              New board
            </button>
          )}

          <select
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            className="ml-auto rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1.5 text-sm text-slate-300 outline-none focus:border-ember-500"
          >
            <option value="">All assignees</option>
            <option value={UNASSIGNED_FILTER_VALUE}>Unassigned</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.full_name}
              </option>
            ))}
          </select>
        </div>

        {activeBoard ? (
          <KanbanBoard
            columns={activeBoard.columns}
            issues={filteredIssues}
            members={members}
            projectId={project.id}
            onMoveIssue={handleMoveIssue}
            onCreateColumn={handleCreateColumn}
            onRenameColumn={handleRenameColumn}
            onDeleteColumn={handleDeleteColumn}
          />
        ) : (
          <p className="text-sm text-slate-500">No boards yet.</p>
        )}
      </div>
    </AppShell>
  );
}
