// US4 — audit log. Spec: 002-flagpole-web FR-010, FR-011.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AuditList } from "../src/components/AuditList";
import { auditEntry } from "./factories";

const list = (props: Partial<Parameters<typeof AuditList>[0]> = {}) =>
  render(
    <AuditList
      items={[auditEntry(3), auditEntry(2, { flag_key: "other" })]}
      filter=""
      nextBefore={null}
      status="ready"
      message={null}
      onFilter={vi.fn()}
      onLoadMore={vi.fn()}
      onRetry={vi.fn()}
      {...props}
    />,
  );

describe("audit list (US4)", () => {
  it("renders entries in the order received, newest first (US4-1)", () => {
    list();
    const rows = screen.getAllByTestId(/^audit-row-/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual(["audit-row-3", "audit-row-2"]);
    expect(rows[0]).toHaveTextContent("alice@flagpole.local");
    expect(rows[0]).toHaveTextContent("off / 0% → on / 25%");
  });

  it("labels a creation entry instead of showing empty fields (US4-4)", () => {
    list({ items: [auditEntry(1, { env: null, before: null, after: { description: "d" } })] });
    expect(screen.getByTestId("audit-row-1")).toHaveTextContent("created");
  });

  it("reports the filter the user types (US4-2)", async () => {
    const onFilter = vi.fn();
    list({ onFilter });
    await userEvent.type(screen.getByTestId("audit-filter"), "new");
    expect(onFilter).toHaveBeenCalled();
  });

  it("offers older entries only when the service returned a cursor (US4-3)", async () => {
    const onLoadMore = vi.fn();
    const { unmount } = list();
    expect(screen.queryByTestId("audit-load-more")).not.toBeInTheDocument();
    unmount();
    list({ nextBefore: 2, onLoadMore });
    await userEvent.click(screen.getByTestId("audit-load-more"));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });
});
