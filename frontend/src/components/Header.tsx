// Identity, role and sign in/out. Spec: 002-flagpole-web FR-002, US1.
import type { Session } from "../auth/userManager";

interface HeaderProps {
  session: Session | null;
  view: "flags" | "audit";
  onView: (view: "flags" | "audit") => void;
  onSignIn: () => void;
  onSignOut: () => void;
}

export function Header({ session, view, onView, onSignIn, onSignOut }: HeaderProps) {
  return (
    <header className="header">
      <h1>Flagpole</h1>
      {session ? (
        <>
          <nav>
            <button
              type="button"
              data-testid="nav-flags"
              aria-current={view === "flags"}
              onClick={() => onView("flags")}
            >
              Flags
            </button>
            <button
              type="button"
              data-testid="nav-audit"
              aria-current={view === "audit"}
              onClick={() => onView("audit")}
            >
              Audit log
            </button>
          </nav>
          <span className="spacer" />
          <span data-testid="identity">{session.identity}</span>
          <span className={`role role-${session.role}`} data-testid="role">
            {session.role}
          </span>
          <button type="button" data-testid="sign-out" onClick={onSignOut}>
            Sign out
          </button>
        </>
      ) : (
        <>
          <span className="spacer" />
          <button type="button" data-testid="sign-in" onClick={onSignIn}>
            Sign in
          </button>
        </>
      )}
    </header>
  );
}
