# Decision: local cluster with k3d, ingress owned by this project

- **Problem / trigger**: feature 005 needs a real Kubernetes cluster on a developer's machine, created and destroyed by one command, with ports 80 and 443 so the hosts look like a real deployment.
- **Alternative rejected**: kind (no built-in load balancer, so the ingress story becomes a port-forward and stops resembling anything); minikube (heavier, and its ingress addon is installed outside git); a remote cluster (cost, credentials, and nothing about the lesson needs one).
- **Limits**: one cluster, one node, `--k3s-arg "--disable=traefik@server:*"` so the bundled ingress does not fight ours, ports checked before they are bound, and the cluster is disposable — `k3d cluster delete flagpole` is the whole teardown.
- **Not done**: no multi-node cluster (nothing here tests scheduling), no registry beside the cluster (`k3d image import` is one command and one fewer component to trust), no autoscaling, no monitoring stack.
- **Verification** (2026-09-02): `k3d cluster create` with both ports; `scripts/verify-cluster.sh` reports 43 of 43, including every host answering over TLS and plain HTTP redirecting to it.
