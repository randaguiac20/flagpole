// App shell: session-driven views, no router (research F4). Spec: 002-flagpole-web US1..US4.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

/** Older pages are appended, so a repeated cursor must not produce a repeated row (FR-011). */
function mergeById(current: AuditEntry[], incoming: AuditEntry[]): AuditEntry[] {
  const seen = new Set(current.map((entry) => entry.id));
  return [...current, ...incoming.filter((entry) => !seen.has(entry.id))];
}

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

  // Same reason as auditInFlight below, which this was missing: the effect re-runs on sign-in, on
  // every view switch back to flags, and whenever `api` changes for a token refresh. Two overlapping
  // listFlags calls resolve in whatever order the network decides, and `setFlags(await …)` takes the
  // last one to land — so a stale response can overwrite a fresh one. Dropping the second request is
  // what the audit loader already does; flags simply never got the same treatment.
  const flagsInFlight = useRef(false);

  const loadFlags = useCallback(async () => {
    if (flagsInFlight.current) return;
    flagsInFlight.current = true;
    setFlagStatus("loading");
    try {
      setFlags(await api.listFlags());
      setFlagStatus("ready");
    } catch (err) {
      setFlagMessage(err instanceof Error ? err.message : "could not load flags");
      setFlagStatus("error");
    } finally {
      flagsInFlight.current = false;
    }
  }, [api]);

  // Two clicks inside one request window would send the same cursor twice and append both answers.
  const auditInFlight = useRef(false);

  const loadAudit = useCallback(
    async (before?: number) => {
      if (auditInFlight.current) return;
      auditInFlight.current = true;
      setAuditStatus("loading");
      try {
        const page = await api.listAudit({
          limit: 20,
          ...(before !== undefined ? { before } : {}),
          ...(auditFilter ? { flag_key: auditFilter } : {}),
        });
        setAudit((current) => (before === undefined ? page.items : mergeById(current, page.items)));
        setNextBefore(page.next_before ?? null);
        setAuditStatus("ready");
      } catch (err) {
        setAuditMessage(err instanceof Error ? err.message : "could not load the audit log");
        setAuditStatus("error");
      } finally {
        auditInFlight.current = false;
      }
    },
    [api, auditFilter],
  );

  useEffect(() => {
    if (status !== "signed-in") return;
    // Both loaders set their status to "loading" before awaiting, and that transition is required:
    // coming back to a view whose status is already "ready" would otherwise show the previous data
    // with no indication that it is being refreshed. It is not a wasted render either — on mount the
    // value is already "loading", so React bails out.
    //
    // The rule's own alternatives do not fit. There is nothing to derive during render, the initial
    // state is already correct, and "update it from the event" would scatter the transition across
    // sign-in, view switch, filter change, load-more and two retry buttons — five more places to
    // forget it, to remove one render.
    //
    // The rule also fires arbitrarily here: `loadAudit` on the next line is the same pattern and is
    // not reported, only because it takes a parameter and oxlint follows zero-argument callbacks
    // only. Confirmed with a two-callback reproduction. Gotcha #58.
    //
    // oxlint-disable-next-line react/set-state-in-effect
    if (view === "flags") void loadFlags();
    else void loadAudit();
  }, [status, view, loadFlags, loadAudit]);

  // A success notice belongs to one action. Cleared from the events that end that action rather than
  // from an effect, so it can never sit next to the error of a later save (US3-4).
  const changeView = (next: View) => {
    setSuccess(null);
    setView(next);
  };
  const changeEnv = (next: Env) => {
    setSuccess(null);
    setEnv(next);
  };

  const onSave = async (key: string, target: Env, state: EnvState) => {
    setSuccess(null);
    const updated = await api.setEnvState(key, target, state);
    setFlags((current) => current.map((f) => (f.key === key ? updated : f)));
    setSuccess(`Saved ${key} in ${target}.`);
  };

  const onCreate = async (key: string, description: string) => {
    setSuccess(null);
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
        onView={changeView}
        onSignIn={() => void signIn()}
        onSignOut={() => void signOut()}
      />
      <main>
        {notice ? <Notice kind="error" message={notice} onRetry={() => void signIn()} /> : null}
        {!session ? (
          <p>Sign in to see and change feature flags.</p>
        ) : view === "flags" ? (
          <>
            <EnvTabs value={env} onChange={changeEnv} />
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
