import { describe, expect, it } from "vitest";

import type { TaskResponse } from "../api/client_tasks";
import { buildScheduleRows } from "./SchedulePage";

function task(id: string, parent_task_id: string | null): TaskResponse {
  return { id, parent_task_id, project_id: "project-1", milestone_id: null, title: id, description: null,
    status: "todo", priority: "medium", task_type: "task", assignee_id: null, created_by: null,
    created_at: id, updated_at: id, closed_at: null, closed_at_date: null, parent_assigned_at: id,
    start_date: null, due_date: null, days_planned: null, days_taken: null, urgency: null,
    priority_score: null, schedule_status: null, labels: [], subtasks_total: 0, subtasks_completed: 0 };
}

describe("Schedule hierarchy", () => {
  it("numbers only Task and direct Subtask rows", () => {
    const rows = buildScheduleRows([task("1", null), task("2", "1"), task("3", "2")], new Set(), "entry", "asc");
    expect(rows.map((row) => row.number)).toEqual(["1", "1.1"]);
    expect(Math.max(...rows.map((row) => row.depth))).toBe(1);
    expect(rows.some((row) => row.number === "1.1.1")).toBe(false);
  });
});
