import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthContext";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
}));

vi.mock("../api/client", () => ({
  AUTHENTICATION_EXPIRED_EVENT: "engineops:authentication-expired",
  getCurrentUser: api.getCurrentUser,
}));

const storedValues = new Map<string, string>();
const testStorage: Storage = {
  get length() {
    return storedValues.size;
  },
  clear: () => storedValues.clear(),
  getItem: (key) => storedValues.get(key) ?? null,
  key: (index) => Array.from(storedValues.keys())[index] ?? null,
  removeItem: (key) => storedValues.delete(key),
  setItem: (key, value) => storedValues.set(key, value),
};
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: testStorage,
});

function AuthState() {
  const { token, sessionExpired } = useAuth();
  return (
    <div>
      <span data-testid="token">{token ?? "signed-out"}</span>
      <span data-testid="expired">{sessionExpired ? "expired" : "active"}</span>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("engineops_token", "expired-token");
    api.getCurrentUser.mockResolvedValue({
      id: "user-1",
      email: "user@example.com",
      full_name: "Test User",
      is_active: true,
      created_at: "2026-10-02T00:00:00Z",
      roles: [],
    });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("clears the stored session when an authenticated request returns 401", async () => {
    render(
      <AuthProvider>
        <AuthState />
      </AuthProvider>,
    );

    await waitFor(() => expect(api.getCurrentUser).toHaveBeenCalledWith("expired-token"));
    window.dispatchEvent(new Event("engineops:authentication-expired"));

    await waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("signed-out");
      expect(screen.getByTestId("expired")).toHaveTextContent("expired");
    });
    expect(localStorage.getItem("engineops_token")).toBeNull();
  });
});
