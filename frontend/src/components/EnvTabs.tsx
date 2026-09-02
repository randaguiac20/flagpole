// Environment tabs. Spec: 002-flagpole-web FR-005 (US2-2).
import type { Env } from "../api/client";

const ENVS: Env[] = ["dev", "prod"];

export function EnvTabs({ value, onChange }: { value: Env; onChange: (env: Env) => void }) {
  return (
    <div className="tabs" role="tablist" aria-label="Environment">
      {ENVS.map((env) => (
        <button
          key={env}
          type="button"
          role="tab"
          data-testid={`env-tab-${env}`}
          aria-selected={value === env}
          onClick={() => onChange(env)}
        >
          {env}
        </button>
      ))}
    </div>
  );
}
