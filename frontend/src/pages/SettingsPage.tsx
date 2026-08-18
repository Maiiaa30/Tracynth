import { useMutation } from '@tanstack/react-query';
import { PageHeader, Section } from '../components/Page';
import { ResourceTable } from '../components/ResourceTable';
import { useResource } from '../hooks/useResource';
import { text } from '../lib/format';
import { apiRequest, displayError } from '../lib/api';

export function SettingsPage() {
  const settings = useResource('/settings/');
  const signOutAll = useMutation({
    mutationFn: () => apiRequest('/auth/logout-all/', { method: 'POST' }),
    onSuccess: () => window.location.assign('/login'),
  });
  return (
    <>
      <PageHeader
        title="Settings"
        description="Non-secret operator policy reported by the server."
      />
      <Section
        title="Application policy"
        description="Secrets are configured through deployment environment or runtime secret files, never here."
      >
        <ResourceTable
          page={settings.data}
          loading={settings.isPending}
          error={settings.error}
          onRetry={() => void settings.refetch()}
          emptyTitle="No configurable policy"
          emptyDetail="This deployment has not exposed any operator-editable settings."
          caption="Application settings"
          columns={[
            {
              label: 'Setting',
              render: (row) => <strong>{text(row.label ?? row.key ?? row.name)}</strong>,
            },
            { label: 'Value', render: (row) => text(row.display_value ?? row.value) },
            { label: 'Description', render: (row) => text(row.description) },
          ]}
        />
      </Section>
      <Section
        title="Session security"
        description="Account lifecycle actions require explicit server support."
      >
        <div className="panel__body session-actions">
          <div>
            <strong>Invalidate active sessions</strong>
            <p className="field-help">
              This signs out every active operator session, including this one.
            </p>
          </div>
          <button
            className="button button--secondary"
            type="button"
            disabled={signOutAll.isPending}
            onClick={() => signOutAll.mutate()}
          >
            {signOutAll.isPending ? 'Signing out…' : 'Sign out all sessions'}
          </button>
          {signOutAll.error ? (
            <p className="form-error session-actions__error" role="alert">
              {displayError(signOutAll.error)}
            </p>
          ) : null}
        </div>
      </Section>
    </>
  );
}
