# UI contract: 002-flagpole-web

The stable surface end-to-end tests and the `ui-tester` agent depend on (FR-012). Changing any identifier here is a spec change.

| `data-testid` | Element | Behavior |
|---|---|---|
| `sign-in` | button (signed out) | starts the redirect flow |
| `sign-out` | button (signed in) | drops the session, returns to the signed-out screen |
| `identity` | text | the user's email |
| `role` | text | `operator` or `viewer` |
| `nav-flags`, `nav-audit` | buttons | switch view |
| `env-tab-dev`, `env-tab-prod` | buttons | select environment; the selected one has `aria-selected="true"` |
| `flag-row-<key>` | row | one per flag |
| `flag-enabled-<key>` | checkbox | enabled state of the selected environment; `disabled` for viewers |
| `flag-rollout-<key>` | number input 0–100 | rollout of the selected environment; `disabled` for viewers |
| `flag-save-<key>` | button | enabled only when the row is dirty and the user is an operator |
| `flag-dirty-<key>` | marker | present only when the row has unsaved edits |
| `flag-error-<key>` | text | the service's message after a refused save |
| `create-key`, `create-description`, `create-submit` | inputs + button | create form; `disabled` for viewers |
| `create-error` | text | the service's message after a refused create; `role="alert"` |
| `viewer-hint` | text | present exactly once on the flags view for viewers (FR-007 scopes it there; the audit view is read-only for everyone) |
| `audit-row-<id>` | row | one per entry |
| `audit-filter` | input | flag key filter |
| `audit-load-more` | button | present only when the service returned a cursor |
| `notice-loading`, `notice-error`, `notice-success` | regions | FR-013; `notice-error` carries a `retry` button as `notice-retry` |

Data shapes come from `specs/001-flagpole-api/contracts/openapi.yaml`; the generated `src/api/schema.d.ts` must be regenerated (and CI's `--check` must pass) whenever that file changes.
