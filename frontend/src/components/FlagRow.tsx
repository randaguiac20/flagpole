// One flag row for the selected environment. Spec: 002-flagpole-web FR-006..009 (US3-1,2,3,4).
import { useState } from "react";
import type { Env, EnvState, Flag } from "../api/client";

export interface FlagRowProps {
  flag: Flag;
  env: Env;
  canEdit: boolean;
  onSave: (key: string, env: Env, state: EnvState) => Promise<void>;
}

const same = (a: EnvState, b: EnvState) =>
  a.enabled === b.enabled && a.rollout_percent === b.rollout_percent;

const ROLLOUT_HINT = "Rollout must be a whole number between 0 and 100.";

export function FlagRow({ flag, env, canEdit, onSave }: FlagRowProps) {
  const saved = flag.environments[env];
  // A pending edit belongs to one (flag, env). Drafts are held per environment, so switching tabs
  // and switching back returns the operator to their own unsaved edit instead of discarding it.
  const [drafts, setDrafts] = useState<Partial<Record<Env, EnvState>>>({});
  const [saving, setSaving] = useState(false);
  // A save failure belongs to the environment it happened in, so it is stored with that environment
  // and simply not shown in the other one — no effect needed to clear it.
  const [failure, setFailure] = useState<{ env: Env; text: string } | null>(null);

  const draft = drafts[env] ?? saved;
  const dirty = !same(draft, saved);
  const message = failure?.env === env ? failure.text : null;

  const setDraft = (next: EnvState) => setDrafts((current) => ({ ...current, [env]: next }));

  const rolloutValid =
    Number.isInteger(draft.rollout_percent) &&
    draft.rollout_percent >= 0 &&
    draft.rollout_percent <= 100;

  const save = async () => {
    setSaving(true);
    setFailure(null);
    try {
      await onSave(flag.key, env, draft);
      // Dropped here, not when the parent's values change: an idempotent save returns what was
      // already stored, so waiting for a value to change would leave the row dirty forever.
      setDrafts((current) => ({ ...current, [env]: undefined }));
    } catch (err) {
      // The draft is kept so the operator does not lose the edit (FR-009).
      setFailure({ env, text: err instanceof Error ? err.message : "could not save the flag" });
    } finally {
      setSaving(false);
    }
  };

  // Save is disabled for an out-of-range rollout (FR-008); say why, so it is not mistaken for the
  // viewer's disabled controls.
  const shown = message ?? (dirty && !rolloutValid ? ROLLOUT_HINT : null);

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
              setDraft({
                ...draft,
                rollout_percent: e.target.value === "" ? NaN : Number(e.target.value),
              })
            }
          />
        </label>
        %
      </td>
      <td>
        <button
          type="button"
          data-testid={`flag-save-${flag.key}`}
          disabled={!canEdit || !dirty || !rolloutValid || saving}
          onClick={save}
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {shown ? (
          <span className="error" role="alert" data-testid={`flag-error-${flag.key}`}>
            {shown}
          </span>
        ) : null}
      </td>
    </tr>
  );
}
