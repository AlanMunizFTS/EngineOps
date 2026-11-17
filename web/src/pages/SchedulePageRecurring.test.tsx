import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SchedulePage from "./SchedulePage";

const api = vi.hoisted(() => ({
  createTask: vi.fn(),
  getProject: vi.fn(),
  listProjectMembers: vi.fn(),
  listProjectTasks: vi.fn(),
  listProjects: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  downloadProjectExport: vi.fn(),
  getProject: api.getProject,
  listProjectMembers: api.listProjectMembers,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_tasks", () => ({
  createSubtask: vi.fn(),
  createTask: api.createTask,
  listProjectTasks: api.listProjectTasks,
  updateTask: vi.fn(),
  updateTaskParent: vi.fn(),
  updateTaskStatus: vi.fn(),
}));

describe("SchedulePage recurring task creation", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision" });
    api.listProjects.mockResolvedValue([]);
    api.listProjectMembers.mockResolvedValue([]);
    api.listProjectTasks.mockResolvedValue([]);
    api.createTask.mockResolvedValue({
      id: "task-1", project_id: "project-1", milestone_id: null, parent_task_id: null,
      title: "Daily check", description: null, status: "backlog", priority: "medium",
      task_type: "task", assignee_id: null, assignee_ids: [], created_by: null,
      created_at: "2026-11-17", updated_at: "2026-11-17", closed_at: null,
      closed_at_date: null, parent_assigned_at: null, start_date: null, due_date: null,
      repeat_daily: true, days_planned: null, days_taken: null, urgency: null,
      priority_score: null, schedule_status: null, labels: [], subtasks_total: 0,
      subtasks_completed: 0,
    });
  });

  it("offers daily recurrence for a top-level activity", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/schedule"]}>
        <Routes>
          <Route path="/projects/:projectId/schedule" element={<SchedulePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "New activity" }));
    fireEvent.change(screen.getByPlaceholderText("Activity title"), {
      target: { value: "Daily check" },
    });
    fireEvent.click(screen.getByLabelText("Repeat every day"));
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(api.createTask).toHaveBeenCalledWith(
      "token",
      "project-1",
      expect.objectContaining({ title: "Daily check", repeat_daily: true }),
    ));
  });
});
