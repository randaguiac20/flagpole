// Audit log. Spec: 002-flagpole-web FR-010, FR-011, FR-013 (US4).
import type { AuditEntry } from "../api/client";
import { Notice } from "./Notice";

interface AuditListProps {
  items: AuditEntry[];
  filter: string;
  nextBefore: number | null;
  status: "loading" | "ready" | "error";
  message: string | null;
  onFilter: (value: string) => void;
  onLoadMore: () => void;
  onRetry: () => void;
}

function describe(entry: AuditEntry): string {
  if (entry.env === null || entry.env === undefined) return "created";
  const before = entry.before;
  const after = entry.after as { enabled?: boolean; rollout_percent?: number };
  const fmt = (s?: { enabled?: boolean; rollout_percent?: number } | null) =>
    s ? `${s.enabled ? "on" : "off"} / ${s.rollout_percent}%` : "—";
  return `${fmt(before)} → ${fmt(after)}`;
}

export function AuditList({
  items,
  filter,
  nextBefore,
  status,
  message,
  onFilter,
  onLoadMore,
  onRetry,
}: AuditListProps) {
  return (
    <section>
      <label>
        Filter by flag
        <input
          data-testid="audit-filter"
          value={filter}
          placeholder="flag key"
          onChange={(e) => onFilter(e.target.value)}
        />
      </label>
      {status === "loading" ? <Notice kind="loading" message="Loading the audit log…" /> : null}
      {status === "error" ? (
        <Notice kind="error" message={message ?? "could not load the audit log"} onRetry={onRetry} />
      ) : null}
      <table>
        <thead>
          <tr>
            <th>When</th>
            <th>Who</th>
            <th>Flag</th>
            <th>Environment</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {items.map((entry) => (
            <tr key={entry.id} data-testid={`audit-row-${entry.id}`}>
              <td>{new Date(entry.at).toLocaleString()}</td>
              <td>{entry.who}</td>
              <td>
                <code>{entry.flag_key}</code>
              </td>
              <td>{entry.env ?? "—"}</td>
              <td>{describe(entry)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && status === "ready" ? <p>No entries yet.</p> : null}
      {nextBefore !== null ? (
        <button type="button" data-testid="audit-load-more" onClick={onLoadMore}>
          Load older entries
        </button>
      ) : null}
    </section>
  );
}
