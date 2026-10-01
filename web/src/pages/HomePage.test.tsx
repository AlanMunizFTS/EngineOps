import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse, TaskStatus } from "../api/client_tasks";
import HomePage from "./HomePage";

const api = vi.hoisted(() => ({
  createTask: vi.fn(),
  getRecentActivity: vi.fn(),
  listProjects: vi.fn(),
  listProjectTasks: vi.fn(),
  updateTask: vi.fn(),
  updateTaskStatus: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    token: "token",
    user: { email: "planner@example.com" },
    logout: vi.fn(),
  }),
}));
vi.mock("../api/client", () => ({
  createProject: vi.fn(),
  getRecentActivity: api.getRecentActivity,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_tasks", () => ({
  createTask: api.createTask,
  listProjectTasks: api.listProjectTasks,
  updateTask: api.updateTask,
  updateTaskStatus: api.updateTaskStatus,
}));
vi.mock("../components/WeeklyPlanBoard", () => ({
  default: ({
    tasks,
    onMoveTask,
    onCreateTask,
    onChangeStatus,
  }: {
    tasks: TaskResponse[];
    onMoveTask: (taskId: string, dueDate: string) => void;
    onCreateTask: (dueDate: string) => void;
    onChangeStatus: (taskId: string, status: TaskStatus) => void;
  }) => (
    <div>
      {tasks.map((task) => (
        <span key={task.id}>{task.title}:{task.due_date}</span>
      ))}
      <button onClick={() => onMoveTask("task-1", "2026-10-02")}>Move task</button>
      <button onClick={() => onCreateTask("2026-10-03")}>New day task</button>
      <button onClick={() => onChangeStatus("task-1", "done")}>Complete task</button>
    </div>
  ),
}));

function task(overrides: Partial<TaskResponse>): TaskResponse {
  return {
    id: "task-1",
    project_id: "project-1",
    milestone_id: null,
    parent_task_id: null,
    title: "Validate camera",
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
    due_date: "2026-10-01",
    days_planned: null,
    days_taken: null,
    urgency: null,
    priority_score: null,
    schedule_status: "on_time",
    labels: [],
    subtasks_total: 0,
    subtasks_completed: 0,
    ...overrides,
  };
}

describe("HomePage weekly plan", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    api.getRecentActivity.mockResolvedValue([]);
    api.listProjects.mockResolvedValue([
      {
        id: "project-1",
        name: "Vision",
        description: null,
        created_by: null,
        created_at: "2026-09-01",
      },
    ]);
    api.listProjectTasks.mockResolvedValue([
      task({}),
      task({ id: "subtask-1", title: "Nested work", parent_task_id: "task-1" }),
    ]);
    api.updateTask.mockResolvedValue(task({ due_date: "2026-10-02" }));
    api.updateTaskStatus.mockResolvedValue(task({ status: "done" }));
    api.createTask.mockResolvedValue(task({ id: "task-2", title: "New inspection", due_date: "2026-10-03" }));
  });

  it("loads only top-level Tasks and persists a dragged due date", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Validate camera:2026-10-01")).toBeInTheDocument();
    expect(screen.queryByText(/Nested work/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Move task" }));

    await waitFor(() =>
      expect(api.updateTask).toHaveBeenCalledWith("token", "task-1", {
        due_date: "2026-10-02",
      }),
    );
    expect(await screen.findByText("Validate camera:2026-10-02")).toBeInTheDocument();
  });

  it("changes status and creates a Task directly from a day", async () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    await screen.findByText("Validate camera:2026-10-01");

    fireEvent.click(screen.getByRole("button", { name: "Complete task" }));
    await waitFor(() =>
      expect(api.updateTaskStatus).toHaveBeenCalledWith("token", "task-1", "done"),
    );

    fireEvent.click(screen.getByRole("button", { name: "New day task" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "New inspection" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Task" }));

    await waitFor(() =>
      expect(api.createTask).toHaveBeenCalledWith("token", "project-1", {
        title: "New inspection",
        due_date: "2026-10-03",
        priority: "medium",
        task_type: "task",
      }),
    );
  });

  it("opens project creation in a modal", async () => {
    render(<MemoryRouter initialEntries={["/projects?create=1"]}><HomePage /></MemoryRouter>);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("New project")).toBeInTheDocument();
  });
});
