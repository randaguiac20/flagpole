# Secrets: SOPS and age

Spec: `005-platform-delivery` FR-013, FR-014, FR-015. Decision: `docs/decisions/secrets-sops.md`.

The repository is public. Every secret in it is encrypted, and the key that opens them lives on the
developer's machine, never in git.

## What is encrypted, and what is not

`.sops.yaml` encrypts **only the values** under `data` and `stringData`, in files under `deploy/` and
`clusters/`. Everything else — the name, the namespace, the labels, the *keys* of the secret — stays
readable:

```yaml
stringData:
    password: ENC[AES256_GCM,data:FpYWaw...,iv:rDk+GL...,tag:SVa+R4...,type:str]
```

That is deliberate. A diff still shows *which* secret changed and *which key* was added, so a change
can be reviewed. Encrypting whole files produces a diff nobody can read, and a review nobody can
perform is the thing that makes people work around a secret store.

## The key

```
~/.config/sops/age/flagpole.agekey     the private key — the only copy
```

`SOPS_AGE_KEY_FILE` in `.env.example` points at it. `make cluster-up` creates it if it is missing and
applies it to the cluster as the `sops-age` Secret in `flux-system`, which is how Flux decrypts.

**There is no backup.** That is the correct trade: a key with a backup somewhere convenient is a key
in the wrong place. If it is lost, see *Recovering* below — the cost is re-encrypting, not losing
data.

## Everyday tasks

```bash
# create or edit a secret (opens $EDITOR with the plaintext, re-encrypts on save)
sops deploy/overlays/dev/postgres-secret.yaml

# encrypt a file you wrote in the clear
sops --encrypt --in-place deploy/overlays/dev/postgres-secret.yaml

# read one value without opening an editor
sops --decrypt deploy/overlays/dev/postgres-secret.yaml | yq '.stringData.password'

# check every committed secret is encrypted (also runs in pre-commit and CI)
scripts/check-sops-secrets.sh
```

## Rotating a value

Edit it with `sops`, commit, push, reconcile. Flux writes the new Secret and restarts what mounts it.
Rotating a *password* is a value change; rotating the *key* is the next section.

## Rotating the age key

1. `age-keygen -o ~/.config/sops/age/flagpole-new.agekey`
2. Add the new recipient to `.sops.yaml` **alongside** the old one.
3. `find deploy clusters -name '*.yaml' -exec sops updatekeys -y {} \;` — re-wraps each file's data
   key for both recipients. The ciphertext of the values does not change.
4. Confirm the cluster can still decrypt, then remove the old recipient and run `updatekeys` again.

Two recipients during the change is the point: at no moment is there a file only the old key opens.

## Recovering when the key is lost

Nothing is lost except the ability to read what is committed. The secrets in this repository are a
demo database password, a client secret and two service key pairs — all regenerable:

1. `age-keygen -o ~/.config/sops/age/flagpole.agekey` and put the new recipient in `.sops.yaml`.
2. Regenerate the service key pairs: `scripts/consumer-keys.sh` and `scripts/mcp-keys.sh`.
3. Write fresh values into each Secret and encrypt them.
4. `make deploy`.

A real deployment would not be recoverable this way, which is exactly why a real deployment keeps the
key in something with an access log — and why this repository says so rather than pretending a file
in a home directory is a key management system.

## What stops a plaintext secret being committed

Two guards, both tested by `make test-hooks`:

- **In the session**: the `secret-guard` PreToolUse hook refuses to write a `kind: Secret` with
  `data`/`stringData` and no SOPS envelope under `deploy/` or `clusters/`. It needs the file's
  content, which a permissions rule cannot inspect.
- **On commit**: `scripts/check-sops-secrets.sh` runs in pre-commit and in CI, so an edit made outside
  Claude Code is caught too. It scans the **staged** copy.

`gitleaks` runs alongside both and covers everything that is not a Kubernetes Secret.
