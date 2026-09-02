# Decision: hook `PreToolUse(Edit|Write)` → `secret-guard.sh`

- **Problem / trigger**: a plaintext `kind: Secret` under `deploy/` or `clusters/` committed once is a leaked credential forever. Serves spec `005-platform-delivery` (SOPS). The rule depends on file *content*, which no permission rule can inspect.
- **Alternative rejected**: `gitleaks` pre-commit only (catches it later, after the file exists on disk); CLAUDE.md rule (request).
- **Limits**: four `if` handlers, `Edit(deploy/**)`, `Write(deploy/**)`, `Edit(clusters/**)`, `Write(clusters/**)` (a hook `if` matches only the tool it names, see gotchas); `timeout: 5`; computes the post-edit content and scans each YAML document for `kind: Secret` + `data|stringData` without a `sops:` block containing `ENC[`. Fail-closed.
- **Not done**: does not verify the SOPS MAC or recipients (that is `sops`' job in CI); does not cover Helm values with inline secrets (none are allowed by the manifests rule). Signal: a secret-bearing file type other than a Secret manifest.
- **Verification**: 8 cases in `make test-hooks`; live on 2026-09-02: writing `deploy/base/probe-secret.yaml` with `stringData` was denied and the file never existed.
