// End-to-end config. Spec: 002-flagpole-web (research F6, SC-005: deterministic runs).
// The suite starts everything it needs: the API, Dex, and the Vite dev server.
import { execFileSync } from "node:child_process";
import { defineConfig } from "@playwright/test";

const WEB_PORT = Number(process.env.FLAGPOLE_WEB_PORT ?? 18010);
const API_PORT = Number(process.env.FLAGPOLE_API_PORT ?? 18000);
const DEX_PORT = Number(process.env.FLAGPOLE_DEX_PORT ?? 18030);
const API_DB = process.env.FLAGPOLE_E2E_DB ?? "sqlite:///./e2e.db";
const API_DB_FILE = API_DB.replace(/^sqlite:\/\/\//, "");

// Rendered here rather than in the Dex webServer command: a webServer whose url already answers is
// reused and its command never runs, so a Dex left over from a run on different ports would keep the
// redirect URIs of that run and every sign-in would fail. The script restarts Dex only if it changed.
execFileSync("../scripts/dex-config.sh", { stdio: "inherit" });

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // one shared API and one seeded state
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0, // determinism is a constitution principle: a flaky test is a bug, not a retry
  reporter: [["html", { outputFolder: "playwright-report", open: "never" }], ["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      name: "API",
      // Deleted first: SC-005 wants every run to start from the same seeded state, and a database
      // kept from the last run carries its flags and audit rows into this one (constitution III).
      command: [
        "bash -c 'cd ../backend",
        `rm -f ${API_DB_FILE}`,
        "export FLAGPOLE_DATABASE_URL=" + API_DB,
        `export FLAGPOLE_OIDC_ISSUER=http://localhost:${DEX_PORT}/dex`,
        "export FLAGPOLE_OIDC_CLIENT_ID=flagpole-web",
        "uv run alembic upgrade head",
        "uv run python -m app.seed", // the demo flag new_banner (FR-015 of 001) must exist
        `exec uv run uvicorn app.main:create_app --factory --port ${API_PORT}'`,
      ].join(" && "),
      url: `http://localhost:${API_PORT}/healthz`,
      timeout: 120_000,
      // Never reused: a server already running holds the previous run's database.
      reuseExistingServer: false,
    },
    {
      name: "Dex",
      command: "docker compose -f ../docker-compose.dev.yaml up -d dex",
      url: `http://localhost:${DEX_PORT}/dex/.well-known/openid-configuration`,
      timeout: 120_000,
      reuseExistingServer: true,
    },
    {
      name: "Web",
      command: "npm run dev",
      url: `http://localhost:${WEB_PORT}`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
