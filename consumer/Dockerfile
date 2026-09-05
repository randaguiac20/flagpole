# flagpole-consumer. Spec: 005-platform-delivery FR-001, FR-002.
#
# The base is pinned by digest, not by tag: python:3.12-slim today and in six months are different
# software with the same name, and a digest makes that difference show up in a diff (FR-002).
# Digest resolved 2026-09-02. Renovate updates it in feature 006.
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS build

# uv is copied from its own published image rather than installed with a script from the internet.
COPY --from=ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 /uv /usr/local/bin/uv

# The build stage uses the SAME path as the runtime stage on purpose: a virtual
# environment records absolute paths in its console scripts, so one built at /build and
# copied to /app produces "exec /app/.venv/bin/uvicorn: no such file or directory".
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

# Dependencies first, so a code change does not re-resolve them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY templates ./templates
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

# No uv, no compiler, no lock file in the image that runs: the build stage keeps all of it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# A fixed uid so the manifests can name it, and a home the process can write to nothing in.
RUN groupadd --system --gid 10001 flagpole \
 && useradd --system --uid 10001 --gid flagpole --no-create-home --shell /usr/sbin/nologin flagpole

WORKDIR /app
COPY --from=build --chown=root:root /app/.venv ./.venv
COPY --from=build --chown=root:root /app/app ./app
COPY --from=build --chown=root:root /app/templates ./templates

# Owned by root, run as flagpole: the process can read its own code and cannot rewrite it, which is
# what makes readOnlyRootFilesystem in the manifests a statement rather than a hope.
USER 10001:10001
EXPOSE 8000

# Readiness in the manifest is what Kubernetes acts on; this is for anyone running the image alone.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
