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
});
