// Session state. Spec: 002-flagpole-web FR-001..004 (research F2: Dex has no end_session_endpoint).
import { useCallback, useEffect, useMemo, useState } from "react";
import type { UserManager } from "oidc-client-ts";
import { createUserManager, sessionFromUser } from "./userManager";
import type { Session } from "./userManager";

export type SessionStatus = "loading" | "signed-out" | "signed-in";

export interface UseSession {
  session: Session | null;
  status: SessionStatus;
  notice: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  onUnauthenticated: () => void;
}

// An authorization code may be redeemed exactly once. React StrictMode mounts effects twice in
// development, so the exchange is memoised per URL: the second call reuses the first promise.
let callbackExchange: { url: string; promise: Promise<Session> } | null = null;

function exchangeOnce(userManager: UserManager, url: string): Promise<Session> {
  if (callbackExchange?.url !== url) {
    callbackExchange = {
      url,
      promise: userManager.signinRedirectCallback(url).then(sessionFromUser),
    };
  }
  return callbackExchange.promise;
}

export function useSession(manager?: UserManager): UseSession {
  const userManager = useMemo(() => manager ?? createUserManager(), [manager]);
  const [session, setSession] = useState<Session | null>(null);
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const finish = (s: Session | null) => {
      if (cancelled) return;
      setSession(s);
      setStatus(s ? "signed-in" : "signed-out");
    };
    const run = async () => {
      try {
        if (window.location.pathname === "/callback") {
          const session = await exchangeOnce(userManager, window.location.href);
          window.history.replaceState({}, "", "/");
          finish(session);
          return;
        }
        const user = await userManager.getUser();
        finish(user && !user.expired ? sessionFromUser(user) : null);
      } catch {
        if (!cancelled) setNotice("Sign-in failed. Please try again.");
        finish(null);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [userManager]);

  const signIn = useCallback(async () => {
    setNotice(null);
    await userManager.signinRedirect();
  }, [userManager]);

  // Dex 2.45.1 publishes no end_session_endpoint, so sign-out drops the token locally (research F2).
  const signOut = useCallback(async () => {
    await userManager.removeUser();
    setSession(null);
    setStatus("signed-out");
    setNotice(null);
  }, [userManager]);

  const onUnauthenticated = useCallback(() => {
    void userManager.removeUser();
    setSession(null);
    setStatus("signed-out");
    setNotice("Your session expired. Please sign in again.");
  }, [userManager]);

  return { session, status, notice, signIn, signOut, onUnauthenticated };
}
