import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import KanbanPage from "./KanbanPage";

const api = vi.hoisted(() => ({
  createTask: vi.fn(),
  getProject: vi.fn(),
  listKanbanBoards: vi.fn(),
  listMilestones: vi.fn(),
  listProjectMembers: vi.fn(),
  listProjects: vi.fn(),
  listProjectTasks: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  getProject: api.getProject,
  listProjectMembers: api.listProjectMembers,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_tasks", () => ({
  createTask: api.createTask,
  createKanbanBoard: vi.fn(),
  createKanbanColumn: vi.fn(),
  deleteKanbanBoard: vi.fn(),
  deleteKanbanColumn: vi.fn(),
  listKanbanBoards: api.listKanbanBoards,
  listMilestones: api.listMilestones,
  listProjectTasks: api.listProjectTasks,
  renameKanbanBoard: vi.fn(),
  updateKanbanColumn: vi.fn(),
  updateTask: vi.fn(),
  updateTaskStatus: vi.fn(),
}));

function task(overrides: Partial<TaskResponse> = {}): TaskResponse {
  return {
    id: "task-1", project_id: "project-1", milestone_id: null, parent_task_id: null,
    title: "New calibration", description: null, status: "todo", priority: "medium", task_type: "task",
    assignee_id: null, assignee_ids: [], created_by: null, created_at: "2026-10-01", updated_at: "2026-10-01",
    closed_at: null, closed_at_date: null, parent_assigned_at: null, start_date: null, due_date: null, repeat_daily: false,
    days_planned: null, days_taken: null, urgency: null, priority_score: null, schedule_status: null,
    labels: [], subtasks_total: 0, subtasks_completed: 0, ...overrides,
  };
}

describe("KanbanPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision" });
    api.listProjects.mockResolvedValue([]);
    api.listKanbanBoards.mockResolvedValue([{
      id: "board-1", project_id: "project-1", name: "Main board", columns: [{
        id: "column-1", board_id: "board-1", name: "To do", order_index: 0, maps_to_statuses: ["todo"],
      }],
    }]);
    api.listProjectTasks.mockResolvedValue([]);
    api.listProjectMembers.mockResolvedValue([]);
    api.listMilestones.mockResolvedValue([]);
    api.createTask.mockResolvedValue(task());
  });

  it("creates a task from the project Kanban in the selected board status", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/kanban"]}>
        <Routes><Route path="/projects/:projectId/kanban" element={<KanbanPage />} /></Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "New task" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "New calibration" } });
    fireEvent.click(screen.getByLabelText("Repeat every day"));
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => expect(api.createTask).toHaveBeenCalledWith(
      "token",
      "project-1",
      expect.objectContaining({ title: "New calibration", status: "todo", repeat_daily: true }),
    ));
  });
});
