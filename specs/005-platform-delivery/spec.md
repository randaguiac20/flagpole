# Feature Specification: platform-delivery

**Feature Branch**: `005-platform-delivery`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "005-platform-delivery: run the whole of Flagpole in a local Kubernetes cluster, changed only through git. Container images for the three services; a k3d cluster whose ingress we own; Flux reconciling this repository; Traefik, cert-manager and Dex installed as releases; PostgreSQL replacing SQLite; two environments as two namespaces from one set of manifests with overlays; secrets encrypted in git and decrypted by the cluster; the cluster refusing what it should. Non-goals: no cloud, no production hosting, no image automation (Renovate covers it in 006), no service mesh, no operator for the database."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The whole product runs in the cluster (Priority: P1)

Someone with a clean checkout runs three documented commands and reaches a working Flagpole in a
browser: they sign in through the identity provider, change a flag, and see the consumer's banner
change — all served from the cluster, not from a terminal full of development servers.

**Why this priority**: Everything else in this feature exists to support it. Until the product runs
in the cluster there is nothing to secure, encrypt or verify.

**Independent Test**: From an empty folder, `make bootstrap && make cluster-up && make deploy`, then
open the dev host in a browser and change a flag.

**Acceptance Scenarios**:

1. **Given** a machine with the documented tools and no cluster, **When** the cluster is created and
   this repository reconciled, **Then** every workload reaches a ready state without manual steps.
2. **Given** the running cluster, **When** the dev host is opened in a browser, **Then** the web app
   loads, sign-in succeeds, and a flag can be changed.
3. **Given** the running cluster, **When** the consumer's host is opened, **Then** it shows the
   decision it acted on for the flag state currently set.
4. **Given** both environments deployed, **When** a flag's state differs between them, **Then** each
   environment's consumer shows its own state and neither can read the other's data.

---

### User Story 2 - The cluster is changed only through git (Priority: P1)

Every change to the running system is a commit. Someone editing a manifest and pushing sees the
cluster follow; someone editing the cluster directly sees it reverted or, in this repository, refused
outright.

**Why this priority**: It is the point of the whole exercise, and it is what makes the environments
reproducible rather than a machine somebody once configured. Equal to US1 because a cluster that
works but is changed by hand teaches the wrong lesson.

**Independent Test**: Change a replica count in a manifest, commit, and watch the cluster follow with
no other command. Then change it back with `kubectl` and watch the change disappear.

**Acceptance Scenarios**:

1. **Given** a committed change to an application manifest, **When** reconciliation runs, **Then**
   the cluster matches the commit without any direct cluster command.
2. **Given** a resource changed directly in the cluster, **When** reconciliation runs, **Then** the
   change is reverted to what the repository says.
3. **Given** a resource removed from the repository, **When** reconciliation runs, **Then** it is
   removed from the cluster too, rather than left behind.
4. **Given** the reconciler is asked for status, **When** it is queried, **Then** every unit reports
   whether it is applied and healthy, and names its revision.

---

### User Story 3 - Secrets are encrypted in git and readable only by the cluster (Priority: P2)

Passwords and keys live in the repository as encrypted files. Anyone can clone the repository without
learning them. The cluster decrypts them; a person without the private key cannot.

**Why this priority**: The repository is public. Committing a plaintext password would be the single
worst outcome of this feature, and no other part of it can be demonstrated safely until this holds.

**Independent Test**: Read a committed secret file — it is unreadable. Then read the same value from
the running cluster, and confirm it is the one the application uses.

**Acceptance Scenarios**:

1. **Given** any committed file that defines a secret, **When** it is read from the repository,
   **Then** its values are ciphertext and its structure is still readable.
2. **Given** the cluster holds the decryption key, **When** reconciliation runs, **Then** the
   applications receive the decrypted values and start.
3. **Given** a person without the private key, **When** they attempt to read a committed secret,
   **Then** they cannot recover its values.
4. **Given** a plaintext secret is staged by mistake, **When** the commit is attempted, **Then** it
   is refused before it can be pushed.

---

### User Story 4 - The cluster refuses what it should (Priority: P3)

The workloads run without privileges they do not need, cannot reach services they have no business
reaching, and the assistant's write access does not exist in the production environment.

**Why this priority**: It is what makes the cluster a demonstration of a defensible deployment rather
than a demonstration of Kubernetes. P3 because the system is observable and useful before it is
hardened, and hardening is easier to explain against something that already runs.

**Independent Test**: Attempt each thing that should be refused — a privileged container, a
connection between namespaces, a write to a production flag from the assistant's server — and see
each refused.

**Acceptance Scenarios**:

1. **Given** the application namespaces, **When** a workload attempts to run as root or with extra
   privileges, **Then** it is rejected before it starts.
2. **Given** the running cluster, **When** a workload in one environment attempts to reach the other
   environment's database, **Then** the connection is refused.
3. **Given** the production environment, **When** the assistant's flag server presents its token,
   **Then** it may read and may not write, because that environment grants it nothing more.
4. **Given** the ingress, **When** a host is opened over plain HTTP, **Then** it is served over TLS
   instead, with a certificate the cluster issued.

---

### Edge Cases

- **The cluster already exists**: creating it again must not destroy data or fail confusingly; it
  reports what it found and stops.
- **Ports 80 and 443 are taken on the host**: refused before anything is created, naming the
  listener, rather than half-creating a cluster that cannot serve.
- **The decryption key is missing**: reconciliation of the secrets fails visibly and says which key
  it wanted, instead of applications starting with empty passwords.
- **An image is not present in the cluster**: the workload reports why it cannot start, and the
  documented command to supply the image is in the message or the runbook.
- **The database is not ready when an application starts**: the application waits and becomes ready
  when the database does, rather than crash-looping into a backoff nobody reads.
- **A migration must run before an application serves**: it runs exactly once per version, and two
  simultaneous application starts do not run it twice.
- **The identity provider's address differs between environments**: each environment's web app is
  configured with its own, without rebuilding the image.

## Clarifications

### Session 2026-09-02

- Q: One database per environment, or one shared instance with two databases? → A: One per
  environment. Isolation then means something a test can show — a workload in one environment simply
  cannot open a connection to the other's database (SC-006). A shared instance would have to be
  reachable from both namespaces, which would leave the network policy demonstrating nothing and the
  separation resting on credentials alone.
- Q: Install the reconciler by bootstrapping from the repository, or install it and point it at the
  repository read-only? → A: Bootstrap. The reconciler then manages its own upgrades from git, which
  is the half of the lesson a read-only source drops. It writes its own manifests into this
  repository and creates a deploy key on the remote, so it is announced and agreed before it runs
  (FR-019).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each of the three services MUST have a container image that runs as a non-root user,
  contains no build tooling, and declares how it reports its own health.
- **FR-002**: Image bases MUST be pinned by digest, so the same tag cannot silently become different
  software.
- **FR-003**: A single command MUST create the local cluster, with the project owning ingress rather
  than whatever the distribution installs by default.
- **FR-004**: The cluster MUST refuse to be created when the ports it needs are in use, naming what
  holds them.
- **FR-005**: The running system MUST be defined entirely by files in this repository; nothing may
  require a manual cluster command to reach its desired state.
- **FR-005a**: The reconciler MUST be installed from this repository and keep itself in step with it,
  so that upgrading it is also a commit.
- **FR-006**: Reconciliation MUST remove resources that have been removed from the repository, and
  MUST revert resources changed directly in the cluster.
- **FR-007**: Reconciliation status MUST be inspectable, reporting per unit whether it is applied and
  healthy and which revision it is at.
- **FR-008**: The two environments MUST come from one set of manifests plus one small overlay each;
  a change that applies to both MUST be made in exactly one place.
- **FR-009**: Each environment MUST be isolated: its own namespace, its own database contents, and
  its own configuration.
- **FR-010**: Ingress MUST serve every host over TLS with a certificate the cluster issued, and
  redirect plain HTTP to it.
- **FR-011**: The identity provider MUST run in the cluster and be reachable at its own host, and the
  web application MUST be told its address as configuration rather than at build time.
- **FR-012**: The flag service MUST use PostgreSQL in the cluster, and its schema MUST be brought up
  to date before it serves requests.
- **FR-012a**: Each environment MUST have its own database instance in its own namespace, so that
  isolation is enforced by the network rather than by credentials alone.
- **FR-013**: Every secret committed to this repository MUST be encrypted, with only the values
  hidden so that reviewing a change remains possible.
- **FR-014**: The cluster MUST decrypt those secrets itself, using a private key that is never
  committed.
- **FR-015**: A plaintext secret MUST be refused before it can be committed.
- **FR-016**: Workloads MUST run without privileges they do not need — no root, no privilege
  escalation, a read-only root filesystem where the software allows it — and the namespaces MUST
  enforce that rather than trust it.
- **FR-017**: Network traffic between the environments MUST be denied, and each workload MUST be
  able to reach only what it needs.
- **FR-018**: The production environment MUST NOT grant the assistant's flag server operator rights
  (001 FR-020); the development environment MAY.
- **FR-019**: The documented commands MUST take a clean machine to a working cluster, and MUST say
  what they will do to anything outside this repository before they do it.
- **FR-020**: Every workload MUST report liveness and readiness, and readiness MUST reflect whether
  it can actually serve.

### Key Entities

- **Image**: one per service, built from this repository, identified by a tag that names a version.
- **Environment**: a namespace, an overlay, a database, a set of hosts, and its own secrets. There
  are exactly two: development and production.
- **Platform component**: something every environment depends on but no environment owns — ingress,
  certificates, identity, database.
- **Reconciliation unit**: a named group of manifests the cluster keeps in step with the repository,
  with its own health and its own dependencies.
- **Encrypted secret**: a committed file whose structure is readable and whose values are not.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a clean machine, the documented commands produce a cluster where every
  reconciliation unit and every workload reports ready, with no step performed by hand.
- **SC-002**: A person can sign in through the browser, change a flag in the development
  environment, and see the consumer's page change — entirely through the cluster.
- **SC-003**: Changing a manifest and committing it changes the cluster, and changing the cluster
  directly does not survive.
- **SC-004**: No plaintext secret exists anywhere in the repository's history or working tree, and
  the scanners confirm it.
- **SC-005**: Every application container runs as a non-root user, and an attempt to run a
  privileged one in an application namespace is rejected.
- **SC-006**: A workload in one environment cannot open a connection to the other environment's
  database.
- **SC-007**: The assistant's flag server can change a flag in development and cannot in production.
- **SC-008**: Every host answers over TLS, and plain HTTP reaches the same page rather than failing.

## Assumptions

- The cluster is **local and disposable**. It is not a production deployment and nothing here should
  be read as one; where a real deployment would differ, the decision records say so.
- The two environments share one cluster because the lesson is the overlay and the isolation, not
  the cost of two control planes. Everything that separates them — namespace, database contents,
  network policy, configuration — is real; the control plane boundary is not.
- Images are built locally and supplied to the cluster for this feature. Publishing them from CI and
  updating their tags automatically is feature 006's work, and the manifests are written so that only
  the tag changes.
- The private decryption key lives outside the repository, in the user's own configuration directory.
  Losing it means re-encrypting the secrets, which is the correct trade for never committing it.
- Anything that touches the host or an account outside this repository — creating a cluster, binding
  privileged ports, writing to the remote repository — is announced before it happens and needs the
  user's agreement.
