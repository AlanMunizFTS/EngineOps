import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { KanbanColumnResponse, TaskResponse } from "../api/client_tasks";
import KanbanBoard from "./KanbanBoard";

function task(overrides: Partial<TaskResponse>): TaskResponse {
  return {
    id: "task-1", project_id: "project-1", milestone_id: "milestone-1", parent_task_id: null,
    title: "Top-level calibration", description: null, status: "todo", priority: "high",
    task_type: "task", assignee_id: null, created_by: null, created_at: "2026-09-01",
    updated_at: "2026-09-01", closed_at: null, closed_at_date: null, parent_assigned_at: null,
    start_date: null, due_date: null, days_planned: null, days_taken: null, urgency: null,
    priority_score: null, schedule_status: null, labels: [], subtasks_total: 2, subtasks_completed: 1,
    ...overrides,
  };
}

describe("KanbanBoard", () => {
  it("renders top-level Tasks with Subtask progress and never renders Subtasks as cards", () => {
    const columns: KanbanColumnResponse[] = [{ id: "column-1", board_id: "board-1", name: "Todo", order_index: 0, maps_to_statuses: ["todo"] }];
    render(<MemoryRouter><KanbanBoard columns={columns} tasks={[
      task({}), task({ id: "subtask-1", title: "Hidden nested work", parent_task_id: "task-1" }),
    ]} members={[]} projectId="project-1" milestoneNameById={new Map([["milestone-1", "Validation"]])}
      onMoveTask={vi.fn()} onUpdateTask={vi.fn()} onCreateColumn={vi.fn()} onRenameColumn={vi.fn()} onDeleteColumn={vi.fn()} /></MemoryRouter>);

    expect(screen.getByText("Top-level calibration")).toBeInTheDocument();
    expect(screen.queryByText("Hidden nested work")).not.toBeInTheDocument();
    expect(screen.getByText("Subtasks: 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("Milestone: Validation")).toBeInTheDocument();
  });
});
