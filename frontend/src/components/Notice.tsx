// Loading / error / success regions. Spec: 002-flagpole-web FR-012, FR-013.
interface NoticeProps {
  kind: "loading" | "error" | "success";
  message: string;
  onRetry?: () => void;
}

export function Notice({ kind, message, onRetry }: NoticeProps) {
  return (
    <p className={`notice notice-${kind}`} data-testid={`notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {message}
      {kind === "error" && onRetry ? (
        <button type="button" data-testid="notice-retry" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </p>
  );
}
