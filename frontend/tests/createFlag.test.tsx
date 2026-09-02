// The create form. Spec: 002-flagpole-web FR-015 (US3-5), FR-007 (viewer).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { CreateFlag } from "../src/components/CreateFlag";

it("creates a flag and clears the form", async () => {
  const onCreate = vi.fn(async () => {});
  render(<CreateFlag canEdit onCreate={onCreate} />);

  await userEvent.type(screen.getByTestId("create-key"), "new_flag");
  await userEvent.type(screen.getByTestId("create-description"), "a description");
  await userEvent.click(screen.getByTestId("create-submit"));

  expect(onCreate).toHaveBeenCalledWith("new_flag", "a description");
  expect(screen.getByTestId("create-key")).toHaveValue("");
  expect(screen.getByTestId("create-description")).toHaveValue("");
  expect(screen.queryByTestId("create-error")).not.toBeInTheDocument();
});

it("shows the service's message when creation is refused and keeps what was typed (FR-015)", async () => {
  const onCreate = vi.fn(async () => {
    throw new Error("flag already exists");
  });
  render(<CreateFlag canEdit onCreate={onCreate} />);

  await userEvent.type(screen.getByTestId("create-key"), "new_banner");
  await userEvent.click(screen.getByTestId("create-submit"));

  expect(await screen.findByTestId("create-error")).toHaveTextContent("flag already exists");
  expect(screen.getByTestId("create-key")).toHaveValue("new_banner");
});

it("is disabled for a viewer (FR-007)", () => {
  render(<CreateFlag canEdit={false} onCreate={vi.fn()} />);
  expect(screen.getByTestId("create-key")).toBeDisabled();
  expect(screen.getByTestId("create-description")).toBeDisabled();
  expect(screen.getByTestId("create-submit")).toBeDisabled();
});
