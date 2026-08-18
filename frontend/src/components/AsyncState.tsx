import { displayError } from '../lib/api';

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <div>
        <strong>Couldn’t load this data</strong>
        <p>{displayError(error)}</p>
      </div>
      {onRetry ? (
        <button className="button button--secondary" type="button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">○</span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}
