import { createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppShell } from './layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { NewScanPage } from './pages/NewScanPage';
import { ScanDetailPage } from './pages/ScanDetailPage';
import { ResourcePage } from './pages/ResourcePage';
import { FileLabPage } from './pages/FileLabPage';
import { ExposureGraphPage } from './pages/ExposureGraphPage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { StatusPill } from './components/Page';
import { dateTime, text } from './lib/format';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: 'scans/new', element: <NewScanPage /> },
          { path: 'scans/:scanId', element: <ScanDetailPage /> },
          {
            path: 'identities',
            element: (
              <ResourcePage
                title="Identity cases"
                description="Authorized identity investigations and their current state."
                path="/identities/?ordering=-created_at"
                emptyTitle="No identity cases"
                emptyDetail="Identity cases created through the API will appear here."
              />
            ),
          },
          { path: 'files', element: <FileLabPage /> },
          { path: 'graph', element: <ExposureGraphPage /> },
          {
            path: 'evidence',
            element: (
              <ResourcePage
                title="Evidence"
                description="Immutable provenance records supporting entities, relationships, and findings."
                path="/evidence/?ordering=-retrieved_at"
                emptyTitle="No evidence records"
                emptyDetail="Collector provenance will appear here when scans produce evidence."
                columns={[
                  {
                    label: 'Source',
                    render: (row) => <strong>{text(row.source ?? row.collector_name)}</strong>,
                  },
                  { label: 'Target', render: (row) => text(row.target) },
                  {
                    label: 'Confidence',
                    render: (row) =>
                      typeof row.confidence === 'number'
                        ? `${Math.round(row.confidence * (row.confidence <= 1 ? 100 : 1))}%`
                        : '—',
                  },
                  {
                    label: 'Retrieved',
                    render: (row) => dateTime(row.retrieved_at ?? row.created_at),
                  },
                ]}
              />
            ),
          },
          {
            path: 'incidents',
            element: (
              <ResourcePage
                title="Incidents"
                description="Credible public disclosure metadata and authorized exact-match imports."
                path="/incidents/?ordering=-published_at"
                emptyTitle="No incidents"
                emptyDetail="Verified public incident metadata will appear here."
                columns={[
                  {
                    label: 'Incident',
                    render: (row) => <strong>{text(row.title ?? row.name)}</strong>,
                  },
                  { label: 'Source', render: (row) => text(row.source) },
                  { label: 'Confidence', render: (row) => text(row.confidence) },
                  {
                    label: 'Published',
                    render: (row) => dateTime(row.published_at ?? row.created_at),
                  },
                ]}
              />
            ),
          },
          {
            path: 'monitoring',
            element: (
              <ResourcePage
                title="Monitoring"
                description="Controlled schedules that create future scans."
                path="/monitoring/?ordering=-created_at"
                emptyTitle="No monitoring schedules"
                emptyDetail="No recurring target monitoring has been configured."
                columns={[
                  { label: 'Target', render: (row) => <strong>{text(row.target)}</strong> },
                  { label: 'Schedule', render: (row) => text(row.schedule ?? row.interval) },
                  {
                    label: 'State',
                    render: (row) => <StatusPill value={row.status ?? row.state} />,
                  },
                  { label: 'Next run', render: (row) => dateTime(row.next_run_at) },
                ]}
              />
            ),
          },
          {
            path: 'alerts',
            element: (
              <ResourcePage
                title="Alerts"
                description="New, changed, removed, and reappeared observations."
                path="/alerts/?ordering=-created_at"
                emptyTitle="No alerts"
                emptyDetail="Changes detected by monitored targets will appear here."
                columns={[
                  {
                    label: 'Alert',
                    render: (row) => (
                      <strong>{text(row.title ?? row.change_type ?? row.type)}</strong>
                    ),
                  },
                  { label: 'Target', render: (row) => text(row.target ?? row.finding) },
                  {
                    label: 'State',
                    render: (row) => (
                      <StatusPill
                        value={row.acknowledged ? 'acknowledged' : (row.status ?? 'open')}
                      />
                    ),
                  },
                  { label: 'Created', render: (row) => dateTime(row.created_at) },
                ]}
              />
            ),
          },
          {
            path: 'reports',
            element: (
              <ResourcePage
                title="Reports"
                description="Generated, evidence-backed investigation exports."
                path="/reports/?ordering=-created_at"
                emptyTitle="No reports"
                emptyDetail="Generated reports will appear here when report creation is enabled."
                columns={[
                  {
                    label: 'Report',
                    render: (row) => <strong>{text(row.title ?? row.name ?? row.id)}</strong>,
                  },
                  { label: 'Format', render: (row) => text(row.format ?? row.content_type) },
                  {
                    label: 'State',
                    render: (row) => <StatusPill value={row.status ?? row.state} />,
                  },
                  { label: 'Created', render: (row) => dateTime(row.created_at) },
                ]}
              />
            ),
          },
          { path: 'settings', element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
