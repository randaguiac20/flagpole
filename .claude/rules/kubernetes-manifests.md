---
paths:
  - "deploy/**/*.yaml"
  - "clusters/**/*.yaml"
---

# Kubernetes, Kustomize and Flux manifests

Loaded only when a manifest under `deploy/` or `clusters/` is read.

- Flux owns the cluster. Never `kubectl apply` anything under `deploy/`; change the file, commit, and run `flux reconcile kustomization <name> --with-source`. (The `gitops-guard` hook denies drift anyway.)
- `kind: Secret` files are committed only SOPS-encrypted: `data`/`stringData` values start with `ENC[AES256_GCM,` and the file has a `sops:` block. Create → `sops --encrypt --in-place`. (The `secret-guard` hook denies plaintext.)
- Every image is `ghcr.io/randaguiac20/<name>:<semver>` in `deploy/base` and pinned by digest where the tool supports it. Renovate bumps tags; humans do not edit them by hand.
- Every HelmRelease pins `spec.chart.spec.version` to an exact version and sets `interval`, `timeout`, `install.remediation`/`upgrade.remediation`. Platform ordering is explicit via `dependsOn`.
- Every workload: `resources.requests/limits`, `readinessProbe` + `livenessProbe`, `securityContext` compatible with PodSecurity `restricted` (non-root, no privilege escalation, drop ALL, seccomp RuntimeDefault, read-only root FS), its own ServiceAccount with `automountServiceAccountToken: false` unless it needs the API.
- Labels: `app.kubernetes.io/name`, `app.kubernetes.io/part-of: flagpole`, `app.kubernetes.io/component`. NetworkPolicies select on these labels; default-deny per namespace.
- Overlays (`dev`, `prod`) only change: namespace, replicas, `ENV`, the seed job, and ingress host. Anything else belongs in `base`.
- Comments in manifests reference the spec requirement they satisfy (`# 005-platform-delivery FR-007`).
