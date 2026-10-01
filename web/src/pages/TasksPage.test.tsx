import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import TasksPage from "./TasksPage";

const api = vi.hoisted(() => ({
  getProject: vi.fn(),
  listProjects: vi.fn(),
  listProjectMembers: vi.fn(),
  listProjectTasks: vi.fn(),
  listMilestones: vi.fn(),
  listProjectLabels: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  getProject: api.getProject,
  listProjects: api.listProjects,
  listProjectMembers: api.listProjectMembers,
}));
vi.mock("../api/client_tasks", () => ({
  attachTaskLabel: vi.fn(),
  createTask: vi.fn(),
  listMilestones: api.listMilestones,
  listProjectLabels: api.listProjectLabels,
  listProjectTasks: api.listProjectTasks,
}));

function task(overrides: Partial<TaskResponse>): TaskResponse {
  return {
    id: "task-1",
    project_id: "project-1",
    milestone_id: null,
    parent_task_id: null,
    title: "Top-level Task",
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
    subtasks_total: 1,
    subtasks_completed: 0,
    ...overrides,
  };
}

describe("TasksPage", () => {
  beforeEach(() => {
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision", description: null });
    api.listProjects.mockResolvedValue([]);
    api.listProjectMembers.mockResolvedValue([]);
    api.listMilestones.mockResolvedValue([]);
    api.listProjectLabels.mockResolvedValue([]);
    api.listProjectTasks.mockResolvedValue([
      task({}),
      task({ id: "subtask-1", title: "Nested Subtask", parent_task_id: "task-1" }),
    ]);
  });

  it("renders only top-level Tasks and their Subtask progress", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/tasks"]}>
        <Routes>
          <Route path="/projects/:projectId/tasks" element={<TasksPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Top-level Task")).toBeInTheDocument();
    expect(screen.queryByText("Nested Subtask")).not.toBeInTheDocument();
    expect(screen.getByText("0 / 1")).toBeInTheDocument();
  });
});
