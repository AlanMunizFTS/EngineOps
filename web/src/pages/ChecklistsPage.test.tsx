import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChecklistsPage from "./ChecklistsPage";

const api = vi.hoisted(() => ({
  addItem: vi.fn(),
  createChecklist: vi.fn(),
  getProject: vi.fn(),
  listChecklists: vi.fn(),
  listProjects: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ token: "token" }) }));
vi.mock("../api/client", () => ({
  getProject: api.getProject,
  listProjects: api.listProjects,
}));
vi.mock("../api/client_checklists", () => ({
  addProjectChecklistItem: api.addItem,
  createProjectChecklist: api.createChecklist,
  deleteProjectChecklist: vi.fn(),
  deleteProjectChecklistItem: vi.fn(),
  listProjectChecklists: api.listChecklists,
}));

describe("ChecklistsPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    api.getProject.mockResolvedValue({ id: "project-1", name: "Vision" });
    api.listProjects.mockResolvedValue([]);
    api.listChecklists.mockResolvedValue([]);
    api.createChecklist.mockResolvedValue({
      id: "checklist-1", project_id: "project-1", name: "Startup", items: [],
    });
    api.addItem.mockResolvedValue({
      id: "item-1", checklist_id: "checklist-1", content: "Inspect guards", position: 0,
    });
  });

  it("creates a reusable checklist and adds an item", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/project-1/checklists"]}>
        <Routes><Route path="/projects/:projectId/checklists" element={<ChecklistsPage />} /></Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Checklist name"), {
      target: { value: "Startup" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create checklist" }));
    await screen.findByRole("heading", { name: "Startup" });
    fireEvent.change(screen.getByLabelText("New item for Startup"), {
      target: { value: "Inspect guards" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(api.addItem).toHaveBeenCalledWith(
      "token", "checklist-1", "Inspect guards",
    ));
    expect(await screen.findByText("Inspect guards")).toBeInTheDocument();
  });
});
