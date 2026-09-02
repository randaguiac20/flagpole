// App shell: session-driven views, no router (research F4). Spec: 002-flagpole-web US1..US4.
import { useCallback, useEffect, useMemo, useState } from "react";
import { createApi } from "./api/client";
import type { AuditEntry, Env, EnvState, Flag } from "./api/client";
import { useSession } from "./auth/useSession";
import { AuditList } from "./components/AuditList";
import { EnvTabs } from "./components/EnvTabs";
import { FlagTable } from "./components/FlagTable";
import { Header } from "./components/Header";
import { Notice } from "./components/Notice";

type View = "flags" | "audit";
type LoadStatus = "loading" | "ready" | "error";

export function App() {
  const { session, status, notice, signIn, signOut, onUnauthenticated } = useSession();
  const [view, setView] = useState<View>("flags");
  const [env, setEnv] = useState<Env>("dev");

  const api = useMemo(
    () => createApi({ getToken: () => session?.accessToken ?? null, onUnauthenticated }),
    [session?.accessToken, onUnauthenticated],
  );

  const [flags, setFlags] = useState<Flag[]>([]);
  const [flagStatus, setFlagStatus] = useState<LoadStatus>("loading");
  const [flagMessage, setFlagMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [auditStatus, setAuditStatus] = useState<LoadStatus>("loading");
  const [auditMessage, setAuditMessage] = useState<string | null>(null);
  const [auditFilter, setAuditFilter] = useState("");
  const [nextBefore, setNextBefore] = useState<number | null>(null);

  const loadFlags = useCallback(async () => {
    setFlagStatus("loading");
    try {
      setFlags(await api.listFlags());
      setFlagStatus("ready");
    } catch (err) {
      setFlagMessage(err instanceof Error ? err.message : "could not load flags");
      setFlagStatus("error");
    }
  }, [api]);

  const loadAudit = useCallback(
    async (before?: number) => {
      setAuditStatus("loading");
      try {
        const page = await api.listAudit({
          limit: 20,
          ...(before !== undefined ? { before } : {}),
          ...(auditFilter ? { flag_key: auditFilter } : {}),
        });
        setAudit((current) => (before === undefined ? page.items : [...current, ...page.items]));
        setNextBefore(page.next_before ?? null);
        setAuditStatus("ready");
      } catch (err) {
        setAuditMessage(err instanceof Error ? err.message : "could not load the audit log");
        setAuditStatus("error");
      }
    },
    [api, auditFilter],
  );

  useEffect(() => {
    if (status !== "signed-in") return;
    if (view === "flags") void loadFlags();
    else void loadAudit();
  }, [status, view, loadFlags, loadAudit]);

  const onSave = async (key: string, target: Env, state: EnvState) => {
    const updated = await api.setEnvState(key, target, state);
    setFlags((current) => current.map((f) => (f.key === key ? updated : f)));
    setSuccess(`Saved ${key} in ${target}.`);
  };

  const onCreate = async (key: string, description: string) => {
    const created = await api.createFlag(key, description);
    setFlags((current) => [...current, created].sort((a, b) => a.key.localeCompare(b.key)));
    setSuccess(`Created ${key}.`);
  };

  if (status === "loading") return <Notice kind="loading" message="Loading…" />;

  return (
    <div className="app">
      <Header
        session={session}
        view={view}
        onView={setView}
        onSignIn={() => void signIn()}
        onSignOut={() => void signOut()}
      />
      <main>
        {notice ? <Notice kind="error" message={notice} /> : null}
        {!session ? (
          <p>Sign in to see and change feature flags.</p>
        ) : view === "flags" ? (
          <>
            <EnvTabs value={env} onChange={setEnv} />
            {success ? <Notice kind="success" message={success} /> : null}
            <FlagTable
              flags={flags}
              env={env}
              canEdit={session.role === "operator"}
              status={flagStatus}
              message={flagMessage}
              onRetry={() => void loadFlags()}
              onSave={onSave}
              onCreate={onCreate}
            />
          </>
        ) : (
          <AuditList
            items={audit}
            filter={auditFilter}
            nextBefore={nextBefore}
            status={auditStatus}
            message={auditMessage}
            onFilter={setAuditFilter}
            onLoadMore={() => void loadAudit(nextBefore ?? undefined)}
            onRetry={() => void loadAudit()}
          />
        )}
      </main>
    </div>
  );
}
