import { Link } from 'react-router-dom';
import { PageHeader, Section, StatusPill } from '../components/Page';
import { ErrorState, LoadingState, EmptyState } from '../components/AsyncState';
import { useResource } from '../hooks/useResource';
import { dateTime, text } from '../lib/format';

const metrics = [
  { path: '/scans/?page_size=1', label: 'Scans' },
  { path: '/findings/?page_size=1', label: 'Findings' },
  { path: '/alerts/?page_size=1&acknowledged=false', label: 'Open alerts' },
  { path: '/evidence/?page_size=1', label: 'Evidence records' },
];

function Metric({ path, label }: { path: string; label: string }) {
  const query = useResource(path);
  return (
    <article className="metric-card">
      <span>{label}</span>
      {query.isPending ? <span className="metric-value metric-value--muted">…</span> : null}
      {query.isError ? (
        <span className="metric-error" title={String(query.error)}>
          Unavailable
        </span>
      ) : null}
      {query.data ? (
        <strong className="metric-value">{query.data.count.toLocaleString()}</strong>
      ) : null}
    </article>
  );
}

export function OverviewPage() {
  const recent = useResource('/scans/?ordering=-created_at&page_size=6', 10_000);
  return (
    <>
      <PageHeader
        eyebrow="Situation room"
        title="Overview"
        description="Live information from your private Tracynth workspace."
        actions={
          <Link className="button" to="/scans/new">
            Start a scan
          </Link>
        }
      />
      <div className="metric-grid">
        {metrics.map((metric) => (
          <Metric key={metric.label} {...metric} />
        ))}
      </div>
      <Section title="Recent scans" description="Current scan state refreshes automatically.">
        {recent.isPending ? <LoadingState label="Loading recent scans" /> : null}
        {recent.isError ? (
          <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
        ) : null}
        {recent.data && recent.data.results.length === 0 ? (
          <EmptyState
            title="No scans yet"
            detail="Start a domain scan to create the first investigation."
          />
        ) : null}
        {recent.data && recent.data.results.length > 0 ? (
          <div className="scan-list">
            {recent.data.results.map((scan, index) => (
              <Link
                className="scan-row"
                to={`/scans/${String(scan.id)}`}
                key={typeof scan.id === 'string' ? scan.id : index}
              >
                <div>
                  <strong>{text(scan.target, 'Untitled target')}</strong>
                  <span>{dateTime(scan.created_at)}</span>
                </div>
                <StatusPill value={scan.status ?? scan.state} />
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        ) : null}
      </Section>
    </>
  );
}
