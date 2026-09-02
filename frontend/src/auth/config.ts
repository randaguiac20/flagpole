// Where the identity provider lives. Spec: 002-flagpole-web FR-001 (research F2).
//
// Read at run time, not baked into the bundle: `import.meta.env` values are inlined by `vite build`,
// so a build-time issuer would pin one image to one environment and feature 005 needs the same
// `flagpole-web` image in both `flagpole-dev` and `flagpole-prod`. `/config.js` is a tiny script the
// container entrypoint rewrites from its environment; in dev it is `public/config.js`.
export interface OidcConfig {
  issuer: string;
  clientId: string;
}

declare global {
  interface Window {
    __FLAGPOLE_CONFIG__?: Partial<{ oidcIssuer: string; oidcClientId: string }>;
  }
}

const DEV_ISSUER = "http://localhost:18030/dex";

export function resolveOidcConfig(): OidcConfig {
  const injected = typeof window === "undefined" ? undefined : window.__FLAGPOLE_CONFIG__;
  const env = import.meta.env;
  return {
    issuer: injected?.oidcIssuer || env.VITE_OIDC_ISSUER || DEV_ISSUER,
    clientId: injected?.oidcClientId || env.VITE_OIDC_CLIENT_ID || "flagpole-web",
  };
}

/**
 * A deployment that never rewrote `/config.js` would send the browser to a `localhost` identity
 * provider it cannot reach, and the only symptom would be a redirect that never comes back. Say so
 * instead (FR-013: every failure is explained).
 */
export function configProblem(config: OidcConfig, location: Location): string | null {
  const issuerIsLocal = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(config.issuer);
  const pageIsLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (issuerIsLocal && !pageIsLocal) {
    return `This deployment still points at the local identity provider (${config.issuer}). Its /config.js was not configured.`;
  }
  return null;
}
