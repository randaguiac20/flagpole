// FR-012, FR-013 — notice regions and the retry action.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Notice } from "../src/components/Notice";

describe("Notice", () => {
  it("renders each kind under its own test id", () => {
    const { unmount } = render(<Notice kind="loading" message="Loading…" />);
    expect(screen.getByTestId("notice-loading")).toHaveTextContent("Loading…");
    unmount();
    render(<Notice kind="success" message="Saved." />);
    expect(screen.getByTestId("notice-success")).toBeInTheDocument();
  });

  it("offers retry on errors", async () => {
    const onRetry = vi.fn();
    render(<Notice kind="error" message="boom" onRetry={onRetry} />);
    await userEvent.click(screen.getByTestId("notice-retry"));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
