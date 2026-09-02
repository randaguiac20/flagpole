// US2 — flag table per environment. Spec: 002-flagpole-web FR-005, FR-013.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FlagTable } from "../src/components/FlagTable";
import { EnvTabs } from "../src/components/EnvTabs";
import { flag } from "./factories";

const noop = async () => {};

const table = (env: "dev" | "prod", status: "loading" | "ready" | "error" = "ready") =>
  render(
    <FlagTable
      flags={[
        flag("alpha", {
          environments: {
            dev: { enabled: true, rollout_percent: 25 },
            prod: { enabled: false, rollout_percent: 0 },
          },
        }),
        flag("beta"),
      ]}
      env={env}
      canEdit
      status={status}
      message={status === "error" ? "could not load flags" : null}
      onRetry={vi.fn()}
      onSave={noop}
      onCreate={noop}
    />,
  );

describe("flag table (US2)", () => {
  it("lists every flag in the order it receives them (US2-1)", () => {
    table("dev");
    const rows = screen.getAllByTestId(/^flag-row-/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual([
      "flag-row-alpha",
      "flag-row-beta",
    ]);
  });

  it("shows the selected environment's state (US2-3)", () => {
    table("dev");
    expect(screen.getByTestId("flag-enabled-alpha")).toBeChecked();
    expect(screen.getByTestId("flag-rollout-alpha")).toHaveValue(25);
  });

  it("shows the other environment's state after switching (US2-2)", () => {
    table("prod");
    expect(screen.getByTestId("flag-enabled-alpha")).not.toBeChecked();
    expect(screen.getByTestId("flag-rollout-alpha")).toHaveValue(0);
  });

  it("marks the selected tab and reports the choice (US2-2)", async () => {
    const onChange = vi.fn();
    render(<EnvTabs value="dev" onChange={onChange} />);
    expect(screen.getByTestId("env-tab-dev")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("env-tab-prod")).toHaveAttribute("aria-selected", "false");
    await userEvent.click(screen.getByTestId("env-tab-prod"));
    expect(onChange).toHaveBeenCalledWith("prod");
  });

  it("shows a loading notice, and an error notice with retry (US2-4, FR-013)", async () => {
    const { unmount } = table("dev", "loading");
    expect(screen.getByTestId("notice-loading")).toBeInTheDocument();
    unmount();
    table("dev", "error");
    expect(screen.getByTestId("notice-error")).toHaveTextContent("could not load flags");
    expect(screen.getByTestId("notice-retry")).toBeInTheDocument();
  });
});
