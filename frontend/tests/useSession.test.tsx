// Spec: 002-flagpole-web FR-002, FR-003, FR-004 (US1-3, US1-4, US1-5).
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { roleFromProfile, sessionFromUser } from "../src/auth/userManager";
import { useSession } from "../src/auth/useSession";
import type { User, UserManager } from "oidc-client-ts";

const user = (profile: Record<string, unknown>): User =>
  ({ access_token: "tok", expires_at: 9999999999, expired: false, profile }) as unknown as User;

function fakeManager(current: User | null) {
  return {
    getUser: vi.fn().mockResolvedValue(current),
    removeUser: vi.fn().mockResolvedValue(undefined),
    signinRedirect: vi.fn().mockResolvedValue(undefined),
    signinRedirectCallback: vi.fn(),
  } as unknown as UserManager;
}

describe("role mapping (FR-002)", () => {
  it("operators group means operator", () => {
    expect(roleFromProfile({ groups: ["operators"] })).toBe("operator");
  });
  it("any other group, or none, means viewer", () => {
    expect(roleFromProfile({ groups: ["viewers"] })).toBe("viewer");
    expect(roleFromProfile({})).toBe("viewer");
  });
  it("identity falls back to sub when there is no email", () => {
    expect(sessionFromUser(user({ sub: "abc" })).identity).toBe("abc");
    expect(sessionFromUser(user({ sub: "abc", email: "a@b.c" })).identity).toBe("a@b.c");
  });
});

describe("useSession", () => {
  it("reports a signed-in session with identity and role", async () => {
    const { result } = renderHook(() =>
      useSession(fakeManager(user({ email: "alice@flagpole.local", groups: ["operators"] }))),
    );
    await waitFor(() => expect(result.current.status).toBe("signed-in"));
    expect(result.current.session?.identity).toBe("alice@flagpole.local");
    expect(result.current.session?.role).toBe("operator");
  });

  it("starts signed out when there is no user", async () => {
    const { result } = renderHook(() => useSession(fakeManager(null)));
    await waitFor(() => expect(result.current.status).toBe("signed-out"));
    expect(result.current.session).toBeNull();
  });

  it("signOut drops the token and returns to signed out (FR-003)", async () => {
    const manager = fakeManager(user({ email: "a@b.c", groups: ["operators"] }));
    const { result } = renderHook(() => useSession(manager));
    await waitFor(() => expect(result.current.status).toBe("signed-in"));
    await act(async () => {
      await result.current.signOut();
    });
    expect(manager.removeUser).toHaveBeenCalled();
    expect(result.current.session).toBeNull();
    expect(result.current.status).toBe("signed-out");
  });

  it("onUnauthenticated clears the session with a notice (FR-004)", async () => {
    const { result } = renderHook(() => useSession(fakeManager(user({ email: "a@b.c" }))));
    await waitFor(() => expect(result.current.status).toBe("signed-in"));
    act(() => result.current.onUnauthenticated());
    expect(result.current.status).toBe("signed-out");
    expect(result.current.notice).toMatch(/expired/i);
  });
});
