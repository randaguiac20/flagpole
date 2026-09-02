# Decision: Traefik instead of ingress-nginx

- **Problem / trigger**: PROMPT.md specified ingress-nginx. That project was archived on 2026-03-24 and upstream says not to deploy it — following the prompt literally would install unmaintained software with no security fixes (gotcha #1).
- **Alternative rejected**: ingress-nginx anyway (unmaintained); Envoy Gateway with the Gateway API (a larger change to every manifest and a second API to teach — recorded in `anti-patterns.md` as the future signal); k3d's bundled Traefik as-is (installed outside git, which defeats the feature).
- **Limits**: chart 41.4.0 pinned, one replica, HTTP redirected to HTTPS at the entry point, plain `Ingress` resources so nothing else in the prompt changes. One Traefik custom resource is used — the strip-prefix middleware — and the application units depend on the unit that installs Traefik because of it.
- **Not done**: no Gateway API migration, no `IngressRoute` resources (plain `Ingress` keeps the manifests portable), no dashboard exposed.
- **Verification** (2026-09-02): every host answers over TLS and plain HTTP returns a redirect; `/api` is stripped before the flag service sees it, which the development proxy also does — the pair being out of step is how an app works locally and 404s in a cluster.
