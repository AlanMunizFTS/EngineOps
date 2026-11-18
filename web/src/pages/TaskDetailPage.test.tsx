import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import TaskDetailPage from "./TaskDetailPage";

afterEach(cleanup);

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
  updateTask: vi.fn(),
  listProjectChecklists: vi.fn(),
  listTaskChecklists: vi.fn(),
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
  updateTask: api.updateTask,
  updateTaskStatus: vi.fn(),
}));
vi.mock("../api/client_checklists", () => ({
  attachChecklistToTask: vi.fn(),
  detachChecklistFromTask: vi.fn(),
  listProjectChecklists: api.listProjectChecklists,
  listTaskChecklists: api.listTaskChecklists,
  setTaskChecklistItemCompleted: vi.fn(),
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
  assignee_ids: [],
  created_by: null,
  created_at: "2026-09-01",
  updated_at: "2026-09-01",
  closed_at: null,
  closed_at_date: null,
  parent_assigned_at: null,
  start_date: null,
  due_date: null,
  repeat_daily: false,
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
    api.listProjectChecklists.mockResolvedValue([]);
    api.listTaskChecklists.mockResolvedValue([]);
    api.deleteTask.mockResolvedValue(undefined);
    api.updateTask.mockResolvedValue({ ...task, due_date: "2026-10-15" });
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

  it("automatically saves field changes without a Save button", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/tasks/task-1"]}>
        <Routes>
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Due date"), {
      target: { value: "2026-10-15" },
    });

    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(api.updateTask).toHaveBeenCalledWith(
        "token",
        "task-1",
        expect.objectContaining({ due_date: "2026-10-15" }),
      ),
    );
  });

  it("allows a top-level Task to repeat every day", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/tasks/task-1"]}>
        <Routes>
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByLabelText("Repeat every day"));

    await waitFor(() =>
      expect(api.updateTask).toHaveBeenCalledWith(
        "token",
        "task-1",
        expect.objectContaining({ repeat_daily: true }),
      ),
    );
  });

  it("shows visible labels for task fields", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/projects/project-1/tasks/task-1"]}>
        <Routes>
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Replace bearing" });
    [
      ["task-title", "Title"], ["task-status", "Status"], ["task-priority", "Priority"],
      ["task-description", "Description"], ["task-type", "Task type"], ["task-milestone", "Milestone"],
      ["task-start-date", "Start date"], ["task-due-date", "Due date"],
    ].forEach(([id, label]) => {
      expect(container.querySelector(`label[for="${id}"]`)).toHaveTextContent(label);
    });
    expect(container.querySelector("legend")).toHaveTextContent("Assignees");
  });
});
