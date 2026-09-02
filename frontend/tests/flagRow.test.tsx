// US3 — operator edits, saves, and failure handling. Spec: 002-flagpole-web FR-006, FR-008, FR-009.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FlagRow } from "../src/components/FlagRow";
import { flag } from "./factories";

const row = (onSave = vi.fn().mockResolvedValue(undefined), canEdit = true) => {
  render(
    <table>
      <tbody>
        <FlagRow flag={flag("new_banner")} env="dev" canEdit={canEdit} onSave={onSave} />
      </tbody>
    </table>,
  );
  return onSave;
};

describe("flag row (US3)", () => {
  it("starts clean with save disabled", () => {
    row();
    expect(screen.queryByTestId("flag-dirty-new_banner")).not.toBeInTheDocument();
    expect(screen.getByTestId("flag-save-new_banner")).toBeDisabled();
  });

  it("marks the row modified and enables save after an edit (US3-2)", async () => {
    row();
    await userEvent.click(screen.getByTestId("flag-enabled-new_banner"));
    expect(screen.getByTestId("flag-dirty-new_banner")).toBeInTheDocument();
    expect(screen.getByTestId("flag-save-new_banner")).toBeEnabled();
  });

  it("saves the edited state exactly once (US3-1, FR-006)", async () => {
    const onSave = row();
    await userEvent.click(screen.getByTestId("flag-enabled-new_banner"));
    const rollout = screen.getByTestId("flag-rollout-new_banner");
    await userEvent.clear(rollout);
    await userEvent.type(rollout, "40");
    await userEvent.click(screen.getByTestId("flag-save-new_banner"));
    await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
    expect(onSave).toHaveBeenCalledWith("new_banner", "dev", { enabled: true, rollout_percent: 40 });
  });

  it("keeps the draft and shows the service's message when the save is refused (US3-4, FR-009)", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("operator role required"));
    row(onSave);
    await userEvent.click(screen.getByTestId("flag-enabled-new_banner"));
    await userEvent.click(screen.getByTestId("flag-save-new_banner"));
    await waitFor(() =>
      expect(screen.getByTestId("flag-error-new_banner")).toHaveTextContent("operator role required"),
    );
    expect(screen.getByTestId("flag-enabled-new_banner")).toBeChecked();
    expect(screen.getByTestId("flag-dirty-new_banner")).toBeInTheDocument();
  });

  it("blocks a rollout outside 0-100 before any request (FR-008)", async () => {
    const onSave = row();
    const rollout = screen.getByTestId("flag-rollout-new_banner");
    await userEvent.clear(rollout);
    await userEvent.type(rollout, "150");
    expect(screen.getByTestId("flag-save-new_banner")).toBeDisabled();
    await userEvent.clear(rollout);
    expect(screen.getByTestId("flag-save-new_banner")).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });
});
