import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { apiRequest, displayError } from '../lib/api';
import { ErrorState, LoadingState } from '../components/AsyncState';
import { PageHeader, Section, StatusPill } from '../components/Page';
import { dateTime, percent, text } from '../lib/format';
import type { ApiRecord } from '../types/api';

export function ScanDetailPage() {
  const { scanId = '' } = useParams();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => apiRequest<ApiRecord>(`/scans/${encodeURIComponent(scanId)}/`),
    enabled: Boolean(scanId),
    refetchInterval: (state) => {
      const status = state.state.data?.status ?? state.state.data?.state;
      return ['queued', 'running', 'pending'].includes(String(status)) ? 3_000 : false;
    },
  });
  const cancel = useMutation({
    mutationFn: () =>
      apiRequest(`/scans/${encodeURIComponent(scanId)}/cancel/`, { method: 'POST' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['scan', scanId] }),
  });

  if (query.isPending) return <LoadingState label="Loading scan" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const scan = query.data;
  const status = scan.status ?? scan.state;
  const canCancel = ['queued', 'running', 'pending'].includes(String(status));
  const modules = Array.isArray(scan.modules) ? scan.modules : [];
  return (
    <>
      <PageHeader
        eyebrow="Scan detail"
        title={text(scan.scope_snapshot ?? scan.target, `Scan ${scanId.slice(0, 8)}`)}
        description={`Created ${dateTime(scan.created_at)}`}
        actions={
          canCancel ? (
            <button
              className="button button--danger"
              type="button"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate()}
            >
              {cancel.isPending ? 'Cancelling…' : 'Cancel scan'}
            </button>
          ) : (
            <Link className="button button--secondary" to="/scans/new">
              New scan
            </Link>
          )
        }
      />
      {cancel.error ? (
        <p className="form-error" role="alert">
          {displayError(cancel.error)}
        </p>
      ) : null}
      <div className="detail-grid">
        <div className="detail-stat">
          <span>Status</span>
          <StatusPill value={status} />
        </div>
        <div className="detail-stat">
          <span>Progress</span>
          <strong>{percent(scan.progress)}</strong>
        </div>
        <div className="detail-stat">
          <span>Updated</span>
          <strong>{dateTime(scan.updated_at)}</strong>
        </div>
      </div>
      <Section title="Modules" description="Collector progress reported by the server.">
        {modules.length ? (
          <div className="module-grid">
            {modules.map((value, index) => {
              const module: ApiRecord =
                typeof value === 'object' && value
                  ? (value as ApiRecord)
                  : { name: typeof value === 'string' ? value : text(value) };
              const moduleKey =
                typeof module.id === 'string'
                  ? module.id
                  : typeof module.name === 'string'
                    ? module.name
                    : index;
              return (
                <article className="module-card" key={moduleKey}>
                  <div>
                    <strong>
                      {text(
                        module.module ?? module.name ?? module.collector,
                        `Module ${index + 1}`,
                      )}
                    </strong>
                    <StatusPill value={module.status ?? module.state} />
                  </div>
                  <span>{percent(module.progress)}</span>
                </article>
              );
            })}
          </div>
        ) : (
          <p className="muted">This API response does not include module details.</p>
        )}
      </Section>
    </>
  );
}
