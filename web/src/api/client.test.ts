import { afterEach, describe, expect, it, vi } from "vitest";

import { AUTHENTICATION_EXPIRED_EVENT, authFetch } from "./client";

describe("authenticated API requests", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("notifies the application when the API rejects an expired token", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Could not validate credentials" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const onExpired = vi.fn();
    window.addEventListener(AUTHENTICATION_EXPIRED_EVENT, onExpired, { once: true });

    await expect(authFetch("expired-token", "/projects")).rejects.toThrow(
      "Could not validate credentials",
    );
    expect(onExpired).toHaveBeenCalledOnce();
  });

  it("formats FastAPI validation details as a readable field error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              type: "string_too_short",
              loc: ["body", "password"],
              msg: "String should have at least 8 characters",
            },
          ],
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(authFetch("token", "/admin/users", { method: "POST" })).rejects.toThrow(
      "password: String should have at least 8 characters",
    );
  });
});
