import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import WeeklyPlanBoard, {
  localDateKey,
  resolveTaskDueDateMove,
  startOfWeek,
} from "./WeeklyPlanBoard";

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
    assignee_ids: [],
    created_by: null,
    created_at: "2026-09-01",
    updated_at: "2026-09-01",
    closed_at: null,
    closed_at_date: null,
    parent_assigned_at: null,
    start_date: null,
    due_date: "2026-09-28",
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

describe("WeeklyPlanBoard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 1, 12));
  });

  afterEach(() => vi.useRealTimers());

  it("renders Monday through Sunday and shows completion state", () => {
    const onCreateTask = vi.fn();
    const onChangeStatus = vi.fn();
    render(
      <MemoryRouter>
        <WeeklyPlanBoard
          projects={[{ id: "project-1", name: "Vision", description: null, created_by: null, created_at: "2026-09-01" }]}
          tasks={[
            task({}),
            task({ id: "task-2", title: "Publish report", due_date: "2026-10-01", status: "done" }),
            task({ id: "task-3", title: "Next week", due_date: "2026-10-05" }),
          ]}
          onMoveTask={vi.fn()}
          onCreateTask={onCreateTask}
          onChangeStatus={onChangeStatus}
        />
      </MemoryRouter>,
    );

    expect(screen.getAllByRole("region")).toHaveLength(7);
    expect(screen.getByText("Validate camera")).toBeInTheDocument();
    expect(screen.getByText("Publish report")).toHaveClass("line-through");
    expect(screen.queryByText("Next week")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Completed")).toBeInTheDocument();
    const monday = screen.getByText("Validate camera").closest("section");
    const thursday = screen.getByText("Publish report").closest("section");
    expect(monday).toHaveClass("bg-amber-500/10");
    expect(monday).toHaveTextContent("In progress");
    expect(thursday).toHaveClass("bg-emerald-500/10");
    expect(thursday).toHaveTextContent("Done");

    fireEvent.click(screen.getByRole("button", { name: "Create task for 2026-10-01" }));
    expect(onCreateTask).toHaveBeenCalledWith("2026-10-01");
    fireEvent.change(screen.getByLabelText("Status for Validate camera"), {
      target: { value: "done" },
    });
    expect(onChangeStatus).toHaveBeenCalledWith("task-1", "done");

    fireEvent.click(screen.getByRole("button", { name: "Filter 2026-09-28 tasks" }));
    fireEvent.click(screen.getByLabelText("Show Validate camera"));
    expect(screen.queryByRole("link", { name: "Validate camera" })).not.toBeInTheDocument();
    expect(screen.getByText("No Tasks selected")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Show Validate camera"));
    expect(screen.getByRole("link", { name: "Validate camera" })).toBeInTheDocument();
  });

  it("uses local Monday boundaries and resolves a drop into a due date update", () => {
    expect(localDateKey(startOfWeek(new Date(2026, 9, 1, 12)))).toBe("2026-09-28");
    expect(
      resolveTaskDueDateMove("task-1", "day:2026-10-02", [task({})]),
    ).toEqual({ taskId: "task-1", dueDate: "2026-10-02" });
    expect(
      resolveTaskDueDateMove("task-1", "day:2026-09-28", [task({})]),
    ).toBeNull();
  });
});
