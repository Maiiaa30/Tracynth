import { PageHeader, Section, StatusPill } from '../components/Page';
import { ResourceTable, type Column } from '../components/ResourceTable';
import { useResource } from '../hooks/useResource';
import { dateTime, text } from '../lib/format';

interface ResourcePageProps {
  title: string;
  description: string;
  path: string;
  emptyTitle: string;
  emptyDetail: string;
  columns?: Column[];
}

const defaultColumns: Column[] = [
  {
    label: 'Name',
    render: (row) => <strong>{text(row.name ?? row.title ?? row.value ?? row.id)}</strong>,
  },
  { label: 'Type', render: (row) => text(row.type ?? row.kind ?? row.category) },
  { label: 'Status', render: (row) => <StatusPill value={row.status ?? row.state} /> },
  { label: 'Updated', render: (row) => dateTime(row.updated_at ?? row.created_at) },
];

export function ResourcePage(props: ResourcePageProps) {
  const query = useResource(props.path);
  const columns = props.columns ?? defaultColumns;
  return (
    <>
      <PageHeader title={props.title} description={props.description} />
      <Section
        title={`${props.title} records`}
        description="Records are loaded directly from the Tracynth API."
      >
        <ResourceTable
          page={query.data}
          columns={columns}
          loading={query.isPending}
          error={query.error}
          onRetry={() => void query.refetch()}
          emptyTitle={props.emptyTitle}
          emptyDetail={props.emptyDetail}
          caption={props.title}
        />
      </Section>
    </>
  );
}
