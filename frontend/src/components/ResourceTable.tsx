import { EmptyState, ErrorState, LoadingState } from './AsyncState';
import type { ApiRecord, Page } from '../types/api';

export interface Column {
  label: string;
  render: (record: ApiRecord) => React.ReactNode;
}

export function ResourceTable({
  page,
  columns,
  loading,
  error,
  onRetry,
  emptyTitle,
  emptyDetail,
  caption,
}: {
  page?: Page<ApiRecord>;
  columns: Column[];
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  emptyTitle: string;
  emptyDetail: string;
  caption: string;
}) {
  if (loading) return <LoadingState label={`Loading ${caption.toLowerCase()}`} />;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (!page?.results.length) return <EmptyState title={emptyTitle} detail={emptyDetail} />;
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th scope="col" key={column.label}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {page.results.map((record, index) => (
            <tr key={typeof record.id === 'string' ? record.id : index}>
              {columns.map((column) => (
                <td key={column.label}>{column.render(record)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="record-count">
        {page.count.toLocaleString()} {page.count === 1 ? 'record' : 'records'}
      </p>
    </div>
  );
}
