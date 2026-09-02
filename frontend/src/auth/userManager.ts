// OIDC client. Spec: 002-flagpole-web FR-001, FR-002, FR-003 (research F1, F2).
import { InMemoryWebStorage, UserManager, WebStorageStateStore } from "oidc-client-ts";
import type { User } from "oidc-client-ts";
import { resolveOidcConfig } from "./config";

export type Role = "operator" | "viewer";
export const OPERATOR_GROUP = "operators"; // same rule as the service (FR-002)

export interface Session {
  accessToken: string;
  identity: string;
  role: Role;
  expiresAt: number;
}

/** Role from the id_token's groups claim; anything else is a viewer (FR-002). */
export function roleFromProfile(profile: Record<string, unknown>): Role {
  const groups = (profile.groups as string[] | undefined) ?? [];
  return groups.includes(OPERATOR_GROUP) ? "operator" : "viewer";
}

export function sessionFromUser(user: User): Session {
  const profile = user.profile as Record<string, unknown>;
  return {
    accessToken: user.access_token,
    identity: (profile.email as string | undefined) ?? (profile.sub as string),
    role: roleFromProfile(profile),
    expiresAt: user.expires_at ?? 0,
  };
}

export function createUserManager(): UserManager {
  const config = resolveOidcConfig();
  return new UserManager({
    authority: config.issuer,
    client_id: config.clientId,
    redirect_uri: `${window.location.origin}/callback`,
    scope: "openid profile email groups", // groups is required for the role (research F2)
    // Token in memory only: never localStorage, never a cookie (FR-003).
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
    // The PKCE verifier and the state are flow secrets. oidc-client-ts defaults this store to
    // localStorage, where they would outlive the tab; sessionStorage ends them with it.
    stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: false,
  });
}
