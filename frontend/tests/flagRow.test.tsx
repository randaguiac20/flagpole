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

it("marks only the edited row dirty (US3-2)", async () => {
  render(
    <table>
      <tbody>
        <FlagRow flag={flag("flag_a")} env="dev" canEdit onSave={vi.fn()} />
        <FlagRow flag={flag("flag_b")} env="dev" canEdit onSave={vi.fn()} />
      </tbody>
    </table>,
  );

  await userEvent.click(screen.getByTestId("flag-enabled-flag_a"));

  expect(screen.getByTestId("flag-dirty-flag_a")).toBeInTheDocument();
  expect(screen.queryByTestId("flag-dirty-flag_b")).not.toBeInTheDocument();
  expect(screen.getByTestId("flag-save-flag_b")).toBeDisabled();
});

it("keeps an edit made in the other environment when the tab comes back (FR-006)", async () => {
  const { rerender } = render(
    <table>
      <tbody>
        <FlagRow flag={flag("flag_a")} env="dev" canEdit onSave={vi.fn()} />
      </tbody>
    </table>,
  );

  await userEvent.clear(screen.getByTestId("flag-rollout-flag_a"));
  await userEvent.type(screen.getByTestId("flag-rollout-flag_a"), "40");

  const rowFor = (env: "dev" | "prod") => (
    <table>
      <tbody>
        <FlagRow flag={flag("flag_a")} env={env} canEdit onSave={vi.fn()} />
      </tbody>
    </table>
  );
  rerender(rowFor("prod"));
  expect(screen.getByTestId("flag-rollout-flag_a")).toHaveValue(0);

  rerender(rowFor("dev"));
  expect(screen.getByTestId("flag-rollout-flag_a")).toHaveValue(40);
});

it("explains an out-of-range rollout instead of only disabling save (FR-008)", async () => {
  render(
    <table>
      <tbody>
        <FlagRow flag={flag("flag_a")} env="dev" canEdit onSave={vi.fn()} />
      </tbody>
    </table>,
  );

  await userEvent.clear(screen.getByTestId("flag-rollout-flag_a"));
  await userEvent.type(screen.getByTestId("flag-rollout-flag_a"), "150");

  expect(screen.getByTestId("flag-save-flag_a")).toBeDisabled();
  expect(screen.getByTestId("flag-error-flag_a")).toHaveTextContent(/between 0 and 100/i);
});

it("clears the dirty marker after a save the service answers with unchanged values (FR-009)", async () => {
  // An idempotent write returns what was already stored, so nothing about the flag prop changes.
  // Waiting for a changed value would leave the row dirty forever.
  const onSave = vi.fn().mockResolvedValue(undefined);
  render(
    <table>
      <tbody>
        <FlagRow flag={flag("flag_a")} env="dev" canEdit onSave={onSave} />
      </tbody>
    </table>,
  );

  await userEvent.click(screen.getByTestId("flag-enabled-flag_a"));
  expect(screen.getByTestId("flag-dirty-flag_a")).toBeInTheDocument();

  await userEvent.click(screen.getByTestId("flag-save-flag_a"));

  await waitFor(() =>
    expect(screen.queryByTestId("flag-dirty-flag_a")).not.toBeInTheDocument(),
  );
  expect(onSave).toHaveBeenCalledWith("flag_a", "dev", { enabled: true, rollout_percent: 0 });
});
