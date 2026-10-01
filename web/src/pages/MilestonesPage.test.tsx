import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MilestonesPage from "./MilestonesPage";

const api = vi.hoisted(() => ({
  getProject: vi.fn(),
  listProjects: vi.fn(),
  listMilestones: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  getProject: api.getProject,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_tasks", () => ({
  createMilestone: vi.fn(),
  listMilestones: api.listMilestones,
}));

describe("MilestonesPage", () => {
  beforeEach(() => {
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision", description: null });
    api.listProjects.mockResolvedValue([]);
    api.listMilestones.mockResolvedValue([
      {
        id: "milestone-1",
        project_id: "project-1",
        title: "Validation Phase",
        description: null,
        status: "open",
        due_date: "2026-10-30",
        created_at: "2026-09-01",
        updated_at: "2026-09-01",
        total_tasks: 2,
        completed_tasks: 1,
        progress_percentage: 50,
      },
    ]);
  });

  it("renders calculated top-level Task progress", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/milestones"]}>
        <Routes>
          <Route path="/projects/:projectId/milestones" element={<MilestonesPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Validation Phase")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });
});
