// The shell wiring: session transitions, load failures, and audit paging.
// Spec: 002-flagpole-web FR-004, FR-011, FR-013 (US1-5, US2-4, US4-2). SC-004 asks for tests that
// fail when the behavior is removed, so each case drives the real App state rather than a prop.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import type { User } from "oidc-client-ts";
import { auditEntry, flag } from "./factories";

const mocks = vi.hoisted(() => ({
  api: {
    listFlags: vi.fn(),
    listAudit: vi.fn(),
    setEnvState: vi.fn(),
    createFlag: vi.fn(),
  },
  captured: { onUnauthenticated: () => {} },
}));

// The real client's 401 handling is covered in client.test.ts; here the client is a stand-in so the
// App's reaction to it can be driven directly. Together the two cover the whole path.
vi.mock("../src/api/client", () => ({
  createApi: (options: { onUnauthenticated: () => void }) => {
    mocks.captured = options;
    return mocks.api;
  },
}));

const user = {
  access_token: "tok-abc",
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  expired: false,
  profile: { email: "alice@flagpole.local", groups: ["operators"], sub: "alice" },
} as unknown as User;

const removeUser = vi.fn(async () => {});
vi.mock("../src/auth/userManager", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/auth/userManager")>();
  return {
    ...actual,
    createUserManager: () => ({
      getUser: async () => user,
      removeUser,
      signinRedirect: vi.fn(async () => {}),
      signinRedirectCallback: vi.fn(),
    }),
  };
});

const { App } = await import("../src/App");

beforeEach(() => {
  vi.clearAllMocks();
  mocks.api.listFlags.mockResolvedValue([flag("new_banner")]);
  mocks.api.listAudit.mockResolvedValue({ items: [], next_before: null });
});

it("returns to the signed-out screen when the service reports unauthenticated (US1-5, FR-004)", async () => {
  mocks.api.listFlags.mockImplementation(async () => {
    mocks.captured.onUnauthenticated();
    throw new Error("missing or invalid token");
  });

  render(<App />);

  expect(await screen.findByTestId("sign-in")).toBeInTheDocument();
  expect(screen.queryByTestId("sign-out")).not.toBeInTheDocument();
  expect(screen.getByTestId("notice-error")).toHaveTextContent(/session expired/i);
  expect(removeUser).toHaveBeenCalled();
});

it("shows an explained error when flags cannot be loaded, and retry refetches (US2-4, FR-013)", async () => {
  mocks.api.listFlags.mockRejectedValueOnce(new Error("service unavailable"));

  render(<App />);

  const notice = await screen.findByTestId("notice-error");
  expect(notice).toHaveTextContent("service unavailable");
  expect(mocks.api.listFlags).toHaveBeenCalledTimes(1);

  await userEvent.click(screen.getByTestId("notice-retry"));

  expect(await screen.findByTestId("flag-row-new_banner")).toBeInTheDocument();
  expect(mocks.api.listFlags).toHaveBeenCalledTimes(2);
});

it("narrows the audit log by flag key (US4-2, FR-011)", async () => {
  render(<App />);
  await screen.findByTestId("flag-row-new_banner");
  await userEvent.click(screen.getByTestId("nav-audit"));
  await waitFor(() => expect(mocks.api.listAudit).toHaveBeenCalled());

  await userEvent.type(screen.getByTestId("audit-filter"), "new_banner");

  await waitFor(() =>
    expect(mocks.api.listAudit).toHaveBeenLastCalledWith(
      expect.objectContaining({ flag_key: "new_banner" }),
    ),
  );
});

it("appends an older page without repeating an entry, and blocks a second click (FR-011)", async () => {
  mocks.api.listAudit.mockResolvedValueOnce({
    items: [auditEntry(3), auditEntry(2)],
    next_before: 2,
  });
  let release: (value: { items: unknown[]; next_before: number | null }) => void = () => {};
  mocks.api.listAudit.mockReturnValueOnce(
    new Promise((resolve) => {
      release = resolve;
    }),
  );

  render(<App />);
  await screen.findByTestId("flag-row-new_banner");
  await userEvent.click(screen.getByTestId("nav-audit"));

  const loadMore = await screen.findByTestId("audit-load-more");
  await userEvent.click(loadMore);
  expect(loadMore).toBeDisabled(); // the second click cannot reach the service

  // The service repeats entry 2 on the cursor boundary; it must not appear twice.
  release({ items: [auditEntry(2), auditEntry(1)], next_before: null });

  await waitFor(() =>
    expect(screen.getAllByTestId(/^audit-row-/)).toHaveLength(3),
  );
  expect(mocks.api.listAudit).toHaveBeenCalledTimes(2);
});

it("drops a success notice when the view changes (US3-4)", async () => {
  mocks.api.setEnvState.mockResolvedValue(
    flag("new_banner", {
      environments: {
        dev: { enabled: true, rollout_percent: 30 },
        prod: { enabled: false, rollout_percent: 0 },
      },
    }),
  );

  render(<App />);
  await screen.findByTestId("flag-row-new_banner");
  await userEvent.click(screen.getByTestId("flag-enabled-new_banner"));
  await userEvent.click(screen.getByTestId("flag-save-new_banner"));

  expect(await screen.findByTestId("notice-success")).toBeInTheDocument();

  await userEvent.click(screen.getByTestId("env-tab-prod"));
  expect(screen.queryByTestId("notice-success")).not.toBeInTheDocument();
});
