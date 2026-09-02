// US1 — header states. Spec: 002-flagpole-web FR-002.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Header } from "../src/components/Header";

const session = (role: "operator" | "viewer") => ({
  accessToken: "tok",
  identity: role === "operator" ? "alice@flagpole.local" : "bob@flagpole.local",
  role,
  expiresAt: 0,
});

describe("header (US1)", () => {
  it("offers only sign-in when signed out (US1-1)", () => {
    render(
      <Header session={null} view="flags" onView={vi.fn()} onSignIn={vi.fn()} onSignOut={vi.fn()} />,
    );
    expect(screen.getByTestId("sign-in")).toBeInTheDocument();
    expect(screen.queryByTestId("identity")).not.toBeInTheDocument();
    expect(screen.queryByTestId("nav-flags")).not.toBeInTheDocument();
  });

  it("shows identity and role when signed in (US1-2, US1-3)", () => {
    render(
      <Header
        session={session("operator")}
        view="flags"
        onView={vi.fn()}
        onSignIn={vi.fn()}
        onSignOut={vi.fn()}
      />,
    );
    expect(screen.getByTestId("identity")).toHaveTextContent("alice@flagpole.local");
    expect(screen.getByTestId("role")).toHaveTextContent("operator");
  });

  it("reports sign-in and sign-out clicks (US1-4)", async () => {
    const onSignIn = vi.fn();
    const onSignOut = vi.fn();
    const { rerender } = render(
      <Header session={null} view="flags" onView={vi.fn()} onSignIn={onSignIn} onSignOut={onSignOut} />,
    );
    await userEvent.click(screen.getByTestId("sign-in"));
    expect(onSignIn).toHaveBeenCalledOnce();
    rerender(
      <Header
        session={session("viewer")}
        view="flags"
        onView={vi.fn()}
        onSignIn={onSignIn}
        onSignOut={onSignOut}
      />,
    );
    expect(screen.getByTestId("role")).toHaveTextContent("viewer");
    await userEvent.click(screen.getByTestId("sign-out"));
    expect(onSignOut).toHaveBeenCalledOnce();
  });
});
