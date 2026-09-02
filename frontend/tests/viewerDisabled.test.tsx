// US3-3, US3-6 — every write control is disabled for viewers. Spec: 002-flagpole-web FR-007, SC-003.
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FlagTable } from "../src/components/FlagTable";
import { flag } from "./factories";

const noop = async () => {};

describe("viewer restrictions", () => {
  it("disables toggle, rollout, save and the create form, and shows one hint", () => {
    render(
      <FlagTable
        flags={[flag("alpha"), flag("beta")]}
        env="dev"
        canEdit={false}
        status="ready"
        message={null}
        onRetry={vi.fn()}
        onSave={noop}
        onCreate={noop}
      />,
    );
    for (const key of ["alpha", "beta"]) {
      expect(screen.getByTestId(`flag-enabled-${key}`)).toBeDisabled();
      expect(screen.getByTestId(`flag-rollout-${key}`)).toBeDisabled();
      expect(screen.getByTestId(`flag-save-${key}`)).toBeDisabled();
    }
    expect(screen.getByTestId("create-key")).toBeDisabled();
    expect(screen.getByTestId("create-description")).toBeDisabled();
    expect(screen.getByTestId("create-submit")).toBeDisabled();
    expect(screen.getAllByTestId("viewer-hint")).toHaveLength(1);
  });

  it("shows no viewer hint for operators", () => {
    render(
      <FlagTable
        flags={[flag("alpha")]}
        env="dev"
        canEdit
        status="ready"
        message={null}
        onRetry={vi.fn()}
        onSave={noop}
        onCreate={noop}
      />,
    );
    expect(screen.queryByTestId("viewer-hint")).not.toBeInTheDocument();
  });
});
