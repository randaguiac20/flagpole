# flagpole-web. Spec: 005-platform-delivery FR-001, FR-002, FR-011.
#
# Bases pinned by digest, resolved 2026-09-02. Renovate updates them in feature 006.
FROM node:24-alpine@sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf AS build

WORKDIR /build

# Dependencies first, so a source change does not reinstall them.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


# nginx-unprivileged, not nginx: the ordinary image binds port 80 as root, which the restricted Pod
# Security Standard rejects. It listens on 8080 and runs as uid 101 already.
FROM nginxinc/nginx-unprivileged:1.31-alpine@sha256:aa8c9087d36d93e9d650c5365f883b421e8214aedbad24ade52b844c583358f1

COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# The one thing written at start: /config.js, from the environment. This is why the same image
# serves both environments without a rebuild — see frontend/src/auth/config.ts, which reads it, and
# gotcha #12: import.meta.env is inlined at build time and could not do this.
COPY docker-entrypoint.d/10-config-js.sh /docker-entrypoint.d/10-config-js.sh

USER 101
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/bin/sh", "-c", "wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1"]
