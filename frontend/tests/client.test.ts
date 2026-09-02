// Spec: 002-flagpole-web FR-004, FR-014.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApi } from "../src/api/client";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

// jsdom's fetch needs an absolute URL; in the browser the app uses the relative "/api" default.
const BASE = "http://localhost/api";

describe("api client", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("attaches the bearer token when signed in", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json([]));
    const api = createApi({ baseUrl: BASE, getToken: () => "tok-123", onUnauthenticated: () => {} });
    await api.listFlags();
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.headers.get("Authorization")).toBe("Bearer tok-123");
  });

  it("omits the header when signed out", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json([]));
    const api = createApi({ baseUrl: BASE, getToken: () => null, onUnauthenticated: () => {} });
    await api.listFlags();
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.headers.get("Authorization")).toBeNull();
  });

  it("calls onUnauthenticated on 401 (FR-004)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: "missing or invalid token" }, 401));
    const onUnauthenticated = vi.fn();
    const api = createApi({ baseUrl: BASE, getToken: () => "bad", onUnauthenticated });
    await expect(api.listFlags()).rejects.toThrow(/missing or invalid token/);
    expect(onUnauthenticated).toHaveBeenCalledOnce();
  });

  it("surfaces the service's detail message on a refused save (FR-009)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: "operator role required" }, 403));
    const api = createApi({ baseUrl: BASE, getToken: () => "tok", onUnauthenticated: () => {} });
    await expect(
      api.setEnvState("new_banner", "dev", { enabled: true, rollout_percent: 40 }),
    ).rejects.toThrow("operator role required");
  });
});
