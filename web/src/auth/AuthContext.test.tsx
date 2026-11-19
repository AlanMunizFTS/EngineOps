import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
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
    vi.useRealTimers();
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

  it("signs out at the JWT expiration time without polling the API", async () => {
    vi.useFakeTimers();
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 60 }));
    const token = `header.${payload}.signature`;
    localStorage.setItem("engineops_token", token);

    render(
      <AuthProvider>
        <AuthState />
      </AuthProvider>,
    );

    await act(async () => Promise.resolve());
    expect(screen.getByTestId("token")).toHaveTextContent(token);
    expect(api.getCurrentUser).toHaveBeenCalledTimes(1);

    act(() => vi.advanceTimersByTime(61_000));

    expect(screen.getByTestId("token")).toHaveTextContent("signed-out");
    expect(screen.getByTestId("expired")).toHaveTextContent("expired");
    expect(api.getCurrentUser).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem("engineops_token")).toBeNull();
  });

  it("does not validate an already expired stored JWT against the API", async () => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 1 }));
    localStorage.setItem("engineops_token", `header.${payload}.signature`);

    render(
      <AuthProvider>
        <AuthState />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("signed-out");
      expect(screen.getByTestId("expired")).toHaveTextContent("expired");
    });
    expect(api.getCurrentUser).not.toHaveBeenCalled();
  });
});
