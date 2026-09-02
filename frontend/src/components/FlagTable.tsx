// Flag table for the selected environment. Spec: 002-flagpole-web FR-005..009, FR-013, FR-015.
import type { Env, EnvState, Flag } from "../api/client";
import { CreateFlag } from "./CreateFlag";
import { FlagRow } from "./FlagRow";
import { Notice } from "./Notice";

interface FlagTableProps {
  flags: Flag[];
  env: Env;
  canEdit: boolean;
  status: "loading" | "ready" | "error";
  message: string | null;
  onRetry: () => void;
  onSave: (key: string, env: Env, state: EnvState) => Promise<void>;
  onCreate: (key: string, description: string) => Promise<void>;
}

export function FlagTable({
  flags,
  env,
  canEdit,
  status,
  message,
  onRetry,
  onSave,
  onCreate,
}: FlagTableProps) {
  if (status === "loading") return <Notice kind="loading" message="Loading flags…" />;
  if (status === "error")
    return <Notice kind="error" message={message ?? "could not load flags"} onRetry={onRetry} />;

  return (
    <section>
      {!canEdit ? (
        <p className="hint" data-testid="viewer-hint">
          You have the viewer role. Changing flags requires the operator role.
        </p>
      ) : null}
      <CreateFlag canEdit={canEdit} onCreate={onCreate} />
      <table>
        <caption>Flags in {env}</caption>
        <thead>
          <tr>
            <th scope="col">Flag</th>
            <th scope="col">Description</th>
            <th scope="col">Enabled ({env})</th>
            <th scope="col">Rollout ({env})</th>
            <th scope="col">
              <span className="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {flags.map((flag) => (
            <FlagRow key={flag.key} flag={flag} env={env} canEdit={canEdit} onSave={onSave} />
          ))}
        </tbody>
      </table>
      {flags.length === 0 ? <p>No flags yet.</p> : null}
    </section>
  );
}
