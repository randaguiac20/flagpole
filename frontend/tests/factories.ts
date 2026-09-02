// Test data shaped like the 001 contract. Spec: 002-flagpole-web.
import type { AuditEntry, Flag } from "../src/api/client";

export const flag = (key: string, overrides: Partial<Flag> = {}): Flag => ({
  key,
  description: `${key} description`,
  created_at: "2026-09-02T10:00:00Z",
  environments: {
    dev: { enabled: false, rollout_percent: 0 },
    prod: { enabled: false, rollout_percent: 0 },
  },
  ...overrides,
});

export const auditEntry = (id: number, overrides: Partial<AuditEntry> = {}): AuditEntry => ({
  id,
  who: "alice@flagpole.local",
  at: "2026-09-02T10:00:00Z",
  flag_key: "new_banner",
  env: "dev",
  before: { enabled: false, rollout_percent: 0 },
  after: { enabled: true, rollout_percent: 25 },
  ...overrides,
});
