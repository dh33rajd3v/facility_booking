interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Loading…" }: LoadingStateProps) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, onRetry }: ErrorStateProps) {
  return (
    <div className="state state--error" role="alert">
      <strong>{title}</strong>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="state">
      <p>{message}</p>
    </div>
  );
}
