import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import TaskDetailPage from "./TaskDetailPage";

const api = vi.hoisted(() => ({
  deleteTask: vi.fn(),
  getProject: vi.fn(),
  getTask: vi.fn(),
  getTaskHistory: vi.fn(),
  listMilestones: vi.fn(),
  listProjectLabels: vi.fn(),
  listProjectMembers: vi.fn(),
  listProjects: vi.fn(),
  listSubtasks: vi.fn(),
  listTaskComments: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  getProject: api.getProject,
  listProjectMembers: api.listProjectMembers,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_tasks", () => ({
  attachTaskLabel: vi.fn(),
  createSubtask: vi.fn(),
  createTaskComment: vi.fn(),
  deleteTask: api.deleteTask,
  detachTaskLabel: vi.fn(),
  getTask: api.getTask,
  getTaskHistory: api.getTaskHistory,
  listMilestones: api.listMilestones,
  listProjectLabels: api.listProjectLabels,
  listSubtasks: api.listSubtasks,
  listTaskComments: api.listTaskComments,
  updateTask: vi.fn(),
  updateTaskStatus: vi.fn(),
}));

const task: TaskResponse = {
  id: "task-1",
  project_id: "project-1",
  milestone_id: null,
  parent_task_id: null,
  title: "Replace bearing",
  description: null,
  status: "todo",
  priority: "medium",
  task_type: "task",
  assignee_id: null,
  created_by: null,
  created_at: "2026-09-01",
  updated_at: "2026-09-01",
  closed_at: null,
  closed_at_date: null,
  parent_assigned_at: null,
  start_date: null,
  due_date: null,
  days_planned: null,
  days_taken: null,
  urgency: null,
  priority_score: null,
  schedule_status: null,
  labels: [],
  subtasks_total: 0,
  subtasks_completed: 0,
};

describe("TaskDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision" });
    api.getTask.mockResolvedValue(task);
    api.getTaskHistory.mockResolvedValue([]);
    api.listMilestones.mockResolvedValue([]);
    api.listProjectLabels.mockResolvedValue([]);
    api.listProjectMembers.mockResolvedValue([]);
    api.listProjects.mockResolvedValue([]);
    api.listSubtasks.mockResolvedValue([]);
    api.listTaskComments.mockResolvedValue([]);
    api.deleteTask.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("deletes the current Task and returns to the Task list", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/tasks/task-1"]}>
        <Routes>
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="/projects/:projectId/tasks" element={<p>Task list</p>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(api.deleteTask).toHaveBeenCalledWith("token", "task-1"));
    expect(await screen.findByText("Task list")).toBeInTheDocument();
  });
});
