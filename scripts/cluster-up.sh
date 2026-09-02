#!/usr/bin/env bash
# Creates the local cluster and installs the reconciler. Spec: 005-platform-delivery FR-003, FR-004,
# FR-014, FR-019 (T012).
#
# Two things here reach outside this repository: binding ports 80 and 443, and writing to the GitHub
# remote. Both are announced before they happen, and the second stops for an answer. A command that
# changes something outside the repository should never be a surprise.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
[[ -f .env ]] && source .env
CLUSTER="${FLAGPOLE_CLUSTER_NAME:-flagpole}"
AGE_KEY="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/flagpole.agekey}"
AGE_KEY="${AGE_KEY/#\~/$HOME}"
OWNER="${FLAGPOLE_GITHUB_OWNER:-randaguiac20}"
REPO="${FLAGPOLE_GITHUB_REPO:-flagpole}"
BRANCH="${FLAGPOLE_GITHUB_BRANCH:-main}"
FLUX_PATH="clusters/local"

say()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
die()  { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

say "tools"
for tool in docker k3d kubectl flux sops age-keygen; do
  command -v "$tool" >/dev/null || die "$tool is not installed — see docs/BLUEPRINT.md"
  printf '  %s\n' "$tool"
done

say "ports"
# Refused before anything is created, naming what holds them (FR-004). Half a cluster that cannot
# serve is worse than no cluster.
for port in 80 443; do
  scripts/ports.sh check "$port" || die "port $port is in use — free it before creating the cluster"
done

say "cluster"
if k3d cluster list -o json | jq -e --arg n "$CLUSTER" '.[] | select(.name == $n)' >/dev/null 2>&1; then
  echo "  k3d cluster '$CLUSTER' already exists — leaving it alone"
else
  echo "  creating k3d cluster '$CLUSTER' (this binds ports 80 and 443 on this machine)"
  # The bundled Traefik is disabled: this project installs its own through Flux, and two ingress
  # controllers claiming the same Ingress resolve by start order (research E1).
  k3d cluster create "$CLUSTER" \
    --k3s-arg "--disable=traefik@server:*" \
    --port "80:80@loadbalancer" \
    --port "443:443@loadbalancer" \
    --wait
fi
kubectl cluster-info >/dev/null || die "the cluster is not answering"

say "hostnames"
if getent hosts dev.flagpole.localhost >/dev/null 2>&1; then
  echo "  *.localhost resolves to loopback — nothing to do"
else
  cat <<'MSG'
  *.localhost does NOT resolve on this machine. Add this line yourself (it needs sudo, which this
  script will not run):

    127.0.0.1 dev.flagpole.localhost prod.flagpole.localhost consumer.dev.flagpole.localhost consumer.prod.flagpole.localhost dex.flagpole.localhost

  Run:  sudo sh -c 'echo "<the line above>" >> /etc/hosts'
MSG
fi

say "decryption key"
if [[ -s "$AGE_KEY" ]]; then
  echo "  using the existing key at $AGE_KEY"
else
  mkdir -p "$(dirname "$AGE_KEY")"; chmod 700 "$(dirname "$AGE_KEY")"
  age-keygen -o "$AGE_KEY" >/dev/null 2>&1
  chmod 600 "$AGE_KEY"
  echo "  created $AGE_KEY"
  echo "  NOTE: this is the only copy. See docs/secrets-sops.md before you lose it."
fi
recipient="$(grep -oE 'age1[a-z0-9]+' "$AGE_KEY" | head -1)"
if ! grep -q "$recipient" .sops.yaml; then
  die ".sops.yaml does not name this key ($recipient) — the cluster could not decrypt anything"
fi

say "flux"
if kubectl -n flux-system get kustomization flux-system >/dev/null 2>&1; then
  echo "  flux is already installed in this cluster — skipping bootstrap"
else
  cat <<MSG
  'flux bootstrap github' will change things OUTSIDE this repository's working tree:

    - commit Flux's own manifests to $FLUX_PATH/flux-system and PUSH to $OWNER/$REPO ($BRANCH)
    - store a GitHub token in the cluster as a Secret so Flux can keep reading that repository

  Nothing else in this script touches GitHub. See docs/decisions/flux-bootstrap.md for why this is
  a bootstrap rather than a read-only source.
MSG
  read -r -p "  Continue? [y/N] " answer
  [[ "$answer" == [yY] ]] || die "  stopped at your request — the cluster exists but has no reconciler"

  command -v gh >/dev/null || die "gh is required to supply the token, or set GITHUB_TOKEN yourself"
  GITHUB_TOKEN="${GITHUB_TOKEN:-$(gh auth token)}"
  export GITHUB_TOKEN
  [[ -n "$GITHUB_TOKEN" ]] || die "no GitHub token available (try: gh auth login)"

  flux bootstrap github \
    --token-auth \
    --personal \
    --owner "$OWNER" \
    --repository "$REPO" \
    --branch "$BRANCH" \
    --path "$FLUX_PATH"
fi

say "decryption key in the cluster"
# Applied by hand exactly once, into flux-system: it is the one thing that cannot come from git,
# because it is what makes reading git's secrets possible. The GitOps hook allows flux-system for
# precisely this reason.
kubectl -n flux-system create secret generic sops-age \
  --from-file=age.agekey="$AGE_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

say "done"
cat <<MSG
  flux get kustomizations          what the reconciler is doing
  make deploy                      import the images and wait for readiness
  scripts/verify-cluster.sh        assert the cluster against its contract
MSG
