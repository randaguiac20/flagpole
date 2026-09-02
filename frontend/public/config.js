// Local development values. The container image ships this file and its entrypoint rewrites it from
// the environment, so one image serves flagpole-dev and flagpole-prod (feature 005). See src/auth/config.ts.
window.__FLAGPOLE_CONFIG__ = {
  oidcIssuer: "http://localhost:18030/dex",
  oidcClientId: "flagpole-web",
};
