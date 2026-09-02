// One flag row for the selected environment. Spec: 002-flagpole-web FR-006..009 (US3-1,2,3,4).
import { useEffect, useState } from "react";
import type { Env, EnvState, Flag } from "../api/client";

export interface FlagRowProps {
  flag: Flag;
  env: Env;
  canEdit: boolean;
  onSave: (key: string, env: Env, state: EnvState) => Promise<void>;
}

const same = (a: EnvState, b: EnvState) =>
  a.enabled === b.enabled && a.rollout_percent === b.rollout_percent;

export function FlagRow({ flag, env, canEdit, onSave }: FlagRowProps) {
  const saved = flag.environments[env];
  const [draft, setDraft] = useState<EnvState>(saved);
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  // A pending edit belongs to one (flag, env): switching tabs shows that environment's own draft.
  useEffect(() => {
    setDraft(saved);
    setStatus("idle");
    setMessage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flag.key, env, saved.enabled, saved.rollout_percent]);

  const dirty = !same(draft, saved);

  const save = async () => {
    setStatus("saving");
    setMessage(null);
    try {
      await onSave(flag.key, env, draft);
      setStatus("idle");
    } catch (err) {
      // The draft is kept so the operator does not lose the edit (FR-009).
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "could not save the flag");
    }
  };

  const rolloutValid = Number.isInteger(draft.rollout_percent) &&
    draft.rollout_percent >= 0 &&
    draft.rollout_percent <= 100;

  return (
    <tr data-testid={`flag-row-${flag.key}`}>
      <td>
        <code>{flag.key}</code>
        {dirty ? (
          <span data-testid={`flag-dirty-${flag.key}`} className="dirty" title="Unsaved changes">
            •
          </span>
        ) : null}
      </td>
      <td title={flag.description} className="description">
        {flag.description}
      </td>
      <td>
        <label>
          <span className="sr-only">Enabled in {env}</span>
          <input
            type="checkbox"
            data-testid={`flag-enabled-${flag.key}`}
            checked={draft.enabled}
            disabled={!canEdit}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
          />
        </label>
      </td>
      <td>
        <label>
          <span className="sr-only">Rollout percent in {env}</span>
          <input
            type="number"
            min={0}
            max={100}
            step={1}
            data-testid={`flag-rollout-${flag.key}`}
            value={Number.isNaN(draft.rollout_percent) ? "" : draft.rollout_percent}
            disabled={!canEdit}
            onChange={(e) =>
              setDraft({ ...draft, rollout_percent: e.target.value === "" ? NaN : Number(e.target.value) })
            }
          />
        </label>
        %
      </td>
      <td>
        <button
          type="button"
          data-testid={`flag-save-${flag.key}`}
          disabled={!canEdit || !dirty || !rolloutValid || status === "saving"}
          onClick={save}
        >
          {status === "saving" ? "Saving…" : "Save"}
        </button>
        {message ? (
          <span className="error" role="alert" data-testid={`flag-error-${flag.key}`}>
            {message}
          </span>
        ) : null}
      </td>
    </tr>
  );
}
