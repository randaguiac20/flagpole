# Ports

Rule (PROMPT.md §5.6, constitution V): nothing binds a port that `scripts/ports.sh` has not checked. The project owns **18000–18099** on the host; anything else is either the k3d load balancer or inside the cluster.

| Service | Where | Port | Set by | Checked by |
|---|---|---|---|---|
| flagpole-api (uvicorn) | host, `make dev` | 18000 | `FLAGPOLE_API_PORT` | `scripts/ports.sh check` in `scripts/dev.sh` |
| flagpole-web (Vite) | host, `make dev` | 18010 | `FLAGPOLE_WEB_PORT` | `strictPort: true`; verified 2026-09-02 |
| flagpole-consumer | host, `make dev` | 18020 | `FLAGPOLE_CONSUMER_PORT` | same |
| Dex (docker compose, dev) | host | 18030 | `FLAGPOLE_DEX_PORT` | same |
| PostgreSQL (docker compose, optional) | host | 18040 | `FLAGPOLE_POSTGRES_PORT` | same |
| Traefik via k3d load balancer | host | 80, 443 | `k3d cluster create -p` | `scripts/cluster-up.sh` |
| Kubernetes API (k3d) | host | 6443 (k3d default, random if taken) | k3d | k3d |
| flagpole-api, consumer, web, dex, postgres | in-cluster Services | 8000, 8000, 8080, 5556, 5432 | manifests | no host binding |
| MCP servers (`playwright`, `flagpole-mcp`) | stdio | none | `.mcp.json` | n/a |

Why 18000+: on the development machine 8000, 5174, 5175 and 8888 were already in use (2026-09-02 survey). Default framework ports are never assumed.

Commands:

```
scripts/ports.sh table          # project ports with live status
scripts/ports.sh check 18000    # exit 1 and print the listener if busy
scripts/ports.sh pick           # first free port in FLAGPOLE_PORT_RANGE
```

## In the cluster (005-platform-delivery)

The cluster binds only 80 and 443, through the k3d load balancer; `scripts/cluster-up.sh` checks both
before creating anything and names the listener if either is taken. Everything else is reached by
hostname, not by port.

| Host | Serves | Namespace |
|---|---|---|
| `dev.flagpole.localhost` | the web app, development | `flagpole-dev` |
| `consumer.dev.flagpole.localhost` | the consumer, development | `flagpole-dev` |
| `prod.flagpole.localhost` | the web app, production | `flagpole-prod` |
| `consumer.prod.flagpole.localhost` | the consumer, production | `flagpole-prod` |
| `dex.flagpole.localhost` | sign-in, shared by both | `dex` |

`*.localhost` resolves to loopback without an `/etc/hosts` entry on this machine — check with
`getent hosts dev.flagpole.localhost`. `cluster-up` prints the fallback line to add if it does not,
and never writes to `/etc/hosts` itself, because that needs `sudo`.

The flag service, the consumer and PostgreSQL keep their usual ports **inside** the cluster (8000,
8000 and 5432 on the Pod network). They are not published to the host: the only way in is the
ingress, which is what makes the network policy meaningful.
