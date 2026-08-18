import { PageHeader, Section, StatusPill } from '../components/Page';
import { ResourceTable } from '../components/ResourceTable';
import { useResource } from '../hooks/useResource';
import { dateTime, text } from '../lib/format';

export function FileLabPage() {
  const files = useResource('/files/?ordering=-created_at');
  return (
    <>
      <PageHeader
        title="File lab"
        description="Review bounded, non-executing metadata extraction and file analysis records."
      />
      <Section
        title="Analyze a file"
        description="Files remain outside the served static tree; this deployment currently exposes file records as read-only."
      >
        <div className="upload-row">
          <label className="file-picker">
            <span>File upload unavailable</span>
            <input type="file" disabled />
          </label>
          <button
            className="button"
            type="button"
            disabled
            title="The server currently exposes /files/ as read-only."
          >
            Upload and analyze
          </button>
        </div>
        <p className="field-help upload-note">
          Upload is disabled because the API does not currently advertise a writable file endpoint.
        </p>
      </Section>
      <Section title="Files">
        <ResourceTable
          page={files.data}
          loading={files.isPending}
          error={files.error}
          onRetry={() => void files.refetch()}
          emptyTitle="No files uploaded"
          emptyDetail="File records and their analysis state will appear here."
          caption="File lab records"
          columns={[
            {
              label: 'File',
              render: (row) => <strong>{text(row.display_name ?? row.name)}</strong>,
            },
            { label: 'Type', render: (row) => text(row.detected_mime_type ?? row.mime_type) },
            {
              label: 'State',
              render: (row) => <StatusPill value={row.analysis_state ?? row.status} />,
            },
            { label: 'Uploaded', render: (row) => dateTime(row.created_at) },
          ]}
        />
      </Section>
    </>
  );
}
