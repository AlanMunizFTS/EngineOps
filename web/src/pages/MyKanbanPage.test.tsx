import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import MyKanbanPage from "./MyKanbanPage";

const api = vi.hoisted(() => ({
  createTask: vi.fn(),
  listMyPendingTasks: vi.fn(),
  listProjects: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    token: "token",
    user: { id: "user-1", email: "ada@example.com", full_name: "Ada" },
  }),
}));
vi.mock("../api/client", () => ({ listProjects: api.listProjects }));
vi.mock("../api/client_tasks", () => ({
  createTask: api.createTask,
  listMyPendingTasks: api.listMyPendingTasks,
  updateTaskStatus: vi.fn(),
}));
vi.mock("../components/PersonalKanbanBoard", () => ({ default: () => <div>Board</div> }));

const createdTask: TaskResponse = {
  id: "task-1", project_id: "project-1", milestone_id: null, parent_task_id: null,
  title: "Daily check", description: null, status: "backlog", priority: "medium",
  task_type: "task", assignee_id: "user-1", assignee_ids: ["user-1"], created_by: "user-1",
  created_at: "2026-11-17", updated_at: "2026-11-17", closed_at: null,
  closed_at_date: null, parent_assigned_at: null, start_date: null, due_date: null,
  repeat_daily: true, days_planned: null, days_taken: null, urgency: null,
  priority_score: null, schedule_status: null, labels: [], subtasks_total: 0,
  subtasks_completed: 0,
};

describe("MyKanbanPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    api.listProjects.mockResolvedValue([{
      id: "project-1", name: "Vision", description: null, created_by: null,
      created_at: "2026-11-17",
    }]);
    api.listMyPendingTasks.mockResolvedValue([]);
    api.createTask.mockResolvedValue(createdTask);
  });

  it("creates a daily recurring task", async () => {
    render(<MemoryRouter><MyKanbanPage /></MemoryRouter>);

    fireEvent.click(await screen.findByRole("button", { name: "New task" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Daily check" } });
    fireEvent.click(screen.getByLabelText("Repeat every day"));
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => expect(api.createTask).toHaveBeenCalledWith(
      "token",
      "project-1",
      expect.objectContaining({ title: "Daily check", repeat_daily: true }),
    ));
  });
});
